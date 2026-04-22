from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple
import time

from sdn_hybrid_lb.algorithms.rr import RoundRobinSelector, SmoothWeightedRoundRobin
from sdn_hybrid_lb.algorithms.genetic import GeneticOptimizer, GAParams, FitnessParams
from sdn_hybrid_lb.utils.models import BackendServer, Capacity, Metrics, FlowBinding, VipConfig
from sdn_hybrid_lb.utils.config import AppConfig
from sdn_hybrid_lb.utils.time import now


FlowKey = Tuple[str, int, int, int]  # (client_ip, client_l4_src, vip_l4_dst, ip_proto)


class HybridLoadBalancer:
    """Hybrid LB:
    - RR/SWRR per-flow for fast decisions
    - GA periodically recomputes weights for long-term optimization
    - Overload gating resolves RR vs GA conflicts (never route to overloaded backend)
    """

    def __init__(self, cfg: AppConfig) -> None:
        self.cfg = cfg
        self.vip = VipConfig(ip=str(cfg.vip["ip"]), mac=str(cfg.vip["mac"]))

        self.backends: List[BackendServer] = []
        for b in cfg.backends:
            cap = b.get("capacity") or {}
            self.backends.append(
                BackendServer(
                    name=str(b["name"]),
                    ip=str(b["ip"]),
                    mac=str(b["mac"]),
                    dpid=int(b["dpid"]),
                    port=int(b["port"]),
                    capacity=Capacity(
                        cpu_cores=float(cap.get("cpu_cores", 1.0)),
                        mem_gb=float(cap.get("mem_gb", 1.0)),
                        bw_mbps=float(cap.get("bw_mbps", 1000.0)),
                    ),
                )
            )

        self._rr = RoundRobinSelector()
        self._swrr = SmoothWeightedRoundRobin()

        ga = cfg.hybrid.ga
        fit = ga.fitness
        self._ga = GeneticOptimizer(
            GAParams(
                population=ga.population,
                generations=ga.generations,
                crossover_rate=ga.crossover_rate,
                mutation_rate=ga.mutation_rate,
                tournament_k=ga.tournament_k,
                elitism=ga.elitism,
                seed=ga.seed,
            ),
            FitnessParams(
                w_cpu=fit.util_weights.cpu,
                w_mem=fit.util_weights.mem,
                w_bw=fit.util_weights.bw,
                w_conn=fit.util_weights.conn,
                overload_threshold=fit.overload_threshold,
                penalty_overload=fit.penalty_overload,
                penalty_variance=fit.penalty_variance,
                sla_latency_ms=fit.sla_latency_ms,
                penalty_sla=fit.penalty_sla,
            ),
        )

        self._last_ga_run = 0.0
        self._weights: Dict[str, float] = {b.name: 1.0 / max(1, len(self.backends)) for b in self.backends}
        self._swrr.set_weights(self.backends, self._weights)

        # Flow bindings for stickiness + active-connection counting
        self._flows: Dict[FlowKey, FlowBinding] = {}

        # Port stats tracking for bandwidth utilization
        # Key: (dpid, port) -> (last_tx_bytes, last_rx_bytes, last_time)
        self._port_stats: Dict[Tuple[int, int], Tuple[int, int, float]] = {}

    # ---------------- Selection ----------------

    def choose_backend(self, flow: FlowKey) -> Optional[BackendServer]:
        self._expire_flows()

        # stickiness (per-flow)
        binding = self._flows.get(flow)
        if binding:
            backend = self._get_backend(binding.backend_name)
            if backend and self._is_eligible(backend):
                # refresh
                binding.last_seen_at = now()
                binding.expires_at = now() + self.cfg.controller.flow_idle_timeout
                return backend
            # else: remove binding
            self._remove_flow(flow)

        eligible = [b for b in self.backends if self._is_eligible(b)]
        if not eligible:
            return None

        # Choose based on RR mode
        if self.cfg.hybrid.rr.mode == "round_robin":
            chosen = self._rr.choose(eligible)
        else:
            self._swrr.set_weights(self.backends, self._weights)
            chosen = self._swrr.choose(eligible)

        if not chosen:
            return None

        # record binding + active connections
        self._add_flow(flow, chosen.name)
        return chosen

    # ---------------- GA Scheduling ----------------

    def maybe_run_ga(self) -> bool:
        interval = float(self.cfg.controller.ga_interval_sec)
        t = now()
        if (t - self._last_ga_run) < interval:
            return False

        self._last_ga_run = t

        # Run GA over current backend snapshot
        weights = self._ga.optimize(self.backends)
        if weights:
            self._weights = weights
            for b in self.backends:
                b.weight = float(weights.get(b.name, 0.0))
            self._swrr.set_weights(self.backends, self._weights)
        return True

    def force_ga(self) -> Dict[str, float]:
        self._last_ga_run = 0.0
        self.maybe_run_ga()
        return dict(self._weights)

    # ---------------- Monitoring Updates ----------------

    def update_backend_util_from_prometheus(
        self,
        backend_name: str,
        cpu_util: Optional[float] = None,
        mem_util: Optional[float] = None,
        latency_ms: Optional[float] = None,
    ) -> None:
        b = self._get_backend(backend_name)
        if not b:
            return
        if cpu_util is not None:
            b.metrics.cpu_util = float(max(0.0, min(1.0, cpu_util)))
        if mem_util is not None:
            b.metrics.mem_util = float(max(0.0, min(1.0, mem_util)))
        if latency_ms is not None:
            b.metrics.latency_ms = float(max(0.0, latency_ms))
        b.metrics.updated_at = now()

    def update_port_bytes(self, dpid: int, port: int, tx_bytes: int, rx_bytes: int) -> None:
        key = (dpid, port)
        t = now()
        prev = self._port_stats.get(key)
        self._port_stats[key] = (int(tx_bytes), int(rx_bytes), t)

        # derive bandwidth for any backend on this port
        backend = self._get_backend_by_port(dpid, port)
        if not backend:
            return

        if prev:
            prev_tx, prev_rx, prev_t = prev
            dt = max(1e-6, t - prev_t)
            dtx = max(0, tx_bytes - prev_tx)
            drx = max(0, rx_bytes - prev_rx)
            # Convert to Mbps (bytes -> bits)
            rate_mbps = ((dtx + drx) * 8.0) / dt / 1_000_000.0
            backend.metrics.throughput_mbps = rate_mbps
            # normalize bw utilization by capacity
            backend.metrics.bw_util = min(1.0, rate_mbps / max(1e-6, backend.capacity.bw_mbps))
            backend.metrics.updated_at = t

    # ---------------- Health / Overload ----------------

    def set_backend_health(self, name: str, healthy: bool) -> bool:
        b = self._get_backend(name)
        if not b:
            return False
        b.healthy = bool(healthy)
        return True

    def _is_eligible(self, backend: BackendServer) -> bool:
        if not backend.healthy:
            return False
        # overload gating (conflict resolution)
        thr = self.cfg.hybrid.overload_threshold
        m = backend.metrics

        if m.cpu_util is not None and m.cpu_util >= thr.cpu:
            return False
        if m.mem_util is not None and m.mem_util >= thr.mem:
            return False
        if m.bw_util is not None and m.bw_util >= thr.bw:
            return False

        # active connections threshold normalized by max observed
        max_conn = max((b.metrics.active_connections for b in self.backends), default=1)
        if max_conn > 0:
            conn_util = m.active_connections / max_conn
            if conn_util >= thr.conn:
                return False

        return True

    # ---------------- Flow tracking ----------------

    def _add_flow(self, flow: FlowKey, backend_name: str) -> None:
        t = now()
        self._flows[flow] = FlowBinding(
            backend_name=backend_name,
            created_at=t,
            last_seen_at=t,
            expires_at=t + self.cfg.controller.flow_idle_timeout,
        )
        b = self._get_backend(backend_name)
        if b:
            b.metrics.active_connections += 1
            b.metrics.updated_at = t

    def _remove_flow(self, flow: FlowKey) -> None:
        binding = self._flows.pop(flow, None)
        if not binding:
            return
        b = self._get_backend(binding.backend_name)
        if b and b.metrics.active_connections > 0:
            b.metrics.active_connections -= 1
            b.metrics.updated_at = now()

    def notify_flow_removed(self, flow: FlowKey) -> None:
        """Optional hook: controller can notify when an OpenFlow rule is removed.

        This makes active-connection counting converge faster than waiting for TTL expiry.
        """
        if flow in self._flows:
            self._remove_flow(flow)

    def _expire_flows(self) -> None:
        t = now()
        expired = [k for k, v in self._flows.items() if v.expires_at <= t]
        for k in expired:
            self._remove_flow(k)

    # ---------------- Lookups / Status ----------------

    def _get_backend(self, name: str) -> Optional[BackendServer]:
        for b in self.backends:
            if b.name == name:
                return b
        return None

    def _get_backend_by_port(self, dpid: int, port: int) -> Optional[BackendServer]:
        for b in self.backends:
            if b.dpid == dpid and b.port == port:
                return b
        return None

    def status(self) -> Dict:
        return {
            "vip": {"ip": self.vip.ip, "mac": self.vip.mac},
            "controller": {
                "ga_interval_sec": self.cfg.controller.ga_interval_sec,
                "poll_interval_sec": self.cfg.controller.poll_interval_sec,
                "rr_mode": self.cfg.hybrid.rr.mode,
            },
            "weights": dict(self._weights),
            "backends": [b.as_dict() for b in self.backends],
            "active_flows": len(self._flows),
        }
