from __future__ import annotations

from typing import Dict, Any, List
import time

from sdn_hybrid_lb.algorithms.hybrid import HybridLoadBalancer
from sdn_hybrid_lb.utils.config import AppConfig


class ResourceOptimizerService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.lb = HybridLoadBalancer(config)
        self.flow_rules: List[Dict[str, Any]] = []
        self.events: List[Dict[str, Any]] = []
        self.total_requests = 0
        self.failed_requests = 0
        self.rr_decisions = 0
        self.ga_runs = 0
        self.sla_target_ms = float(config.hybrid.ga.fitness.sla_latency_ms)
        self.sla_violations = 0
        self._flow_sequence = 0

    def backend_summary(self) -> List[Dict[str, Any]]:
        return [backend.as_dict() for backend in self.lb.backends]

    def update_backend_metric(self, backend_name: str, cpu: float | None = None, mem: float | None = None, latency: float | None = None) -> None:
        self.lb.update_backend_util_from_prometheus(backend_name, cpu, mem, latency)

    def update_backend_metrics(
        self,
        backend_name: str,
        cpu_percent: float | None = None,
        memory_percent: float | None = None,
        bandwidth_percent: float | None = None,
        active_connections: int | None = None,
        latency_ms: float | None = None,
        throughput_mbps: float | None = None,
    ) -> Dict[str, Any]:
        backend = self.lb._get_backend(backend_name)
        if backend is None:
            return {'updated': False, 'error': f'unknown backend {backend_name}'}

        self.lb.update_backend_util_from_prometheus(
            backend_name,
            cpu_util=(cpu_percent / 100.0) if cpu_percent is not None else None,
            mem_util=(memory_percent / 100.0) if memory_percent is not None else None,
            latency_ms=latency_ms,
        )
        if bandwidth_percent is not None:
            backend.metrics.bw_util = max(0.0, min(1.0, float(bandwidth_percent) / 100.0))
        if active_connections is not None:
            backend.metrics.active_connections = int(active_connections)
        if throughput_mbps is not None:
            backend.metrics.throughput_mbps = float(throughput_mbps)
        backend.metrics.updated_at = time.time()

        event = self._record_event('metrics_update', backend=backend.name, payload=backend.metrics.as_dict())
        return {'updated': True, 'backend': backend.as_dict(), 'event': event}

    def update_port_stats(self, dpid: int, port: int, tx_bytes: int, rx_bytes: int) -> Dict[str, Any]:
        self.lb.update_port_bytes(dpid, port, tx_bytes, rx_bytes)
        backend = self.lb._get_backend_by_port(dpid, port)
        event = self._record_event(
            'port_stats',
            backend=backend.name if backend else None,
            payload={'dpid': dpid, 'port': port, 'tx_bytes': tx_bytes, 'rx_bytes': rx_bytes},
        )
        return {
            'updated': backend is not None,
            'backend': backend.as_dict() if backend else None,
            'event': event,
        }

    def set_backend_health(self, backend_name: str, healthy: bool, reason: str | None = None) -> Dict[str, Any]:
        updated = self.lb.set_backend_health(backend_name, healthy)
        backend = self.lb._get_backend(backend_name)
        event = self._record_event(
            'backend_health',
            backend=backend_name,
            payload={'healthy': healthy, 'reason': reason or ('healthy' if healthy else 'fault injected')},
        )
        return {
            'updated': updated,
            'backend': backend.as_dict() if backend else None,
            'event': event,
        }

    def recompute_weights(self) -> Dict[str, float]:
        weights = self.lb.force_ga()
        self.ga_runs += 1
        self._record_event('ga_recompute', payload={'weights': weights})
        return weights

    def build_plan(self) -> Dict[str, Any]:
        weights = self.recompute_weights()
        return {
            'source': 'optimizer',
            'plan_version': '1.0.0',
            'backend_weights': weights,
            'reason': 'hybrid rr+ga recompute',
        }

    def apply_context_feedback(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Translate Component 2 monitoring/ML context into Component 1 allocation input."""
        link_util = payload.get('max_link_utilization_ratio')
        latency = payload.get('latency_ms')
        packet_rate = payload.get('packet_in_rate_per_sec') or payload.get('packet_rate_per_sec')
        controller_cpu = payload.get('controller_cpu_percent')
        recommendation = str(payload.get('recommendation') or '').lower()
        congestion = str(payload.get('congestion') or '').lower()
        load = str(payload.get('load') or '').lower()

        updates: List[Dict[str, Any]] = []
        backends = list(self.lb.backends)
        if link_util is not None or latency is not None or packet_rate is not None or controller_cpu is not None:
            for idx, backend in enumerate(backends):
                active = None
                if packet_rate is not None:
                    active = int(max(0.0, float(packet_rate)) / max(1, len(backends)) / 10.0) + idx
                cpu_percent = None
                if controller_cpu is not None:
                    cpu_percent = min(100.0, max(0.0, float(controller_cpu)) + idx * 2.0)
                bandwidth_percent = None
                if link_util is not None:
                    bandwidth_percent = min(100.0, max(0.0, float(link_util)) * 100.0 + idx * 1.5)
                mem_percent = None
                if load in {'medium', 'high', 'overloaded'}:
                    mem_percent = 70.0 if load == 'medium' else 88.0
                updated = self.update_backend_metrics(
                    backend.name,
                    cpu_percent=cpu_percent,
                    memory_percent=mem_percent,
                    bandwidth_percent=bandwidth_percent,
                    active_connections=active,
                    latency_ms=(float(latency) * (1.0 + idx * 0.03)) if latency is not None else None,
                )
                updates.append({'backend': backend.name, 'updated': updated.get('updated', False)})

        should_recompute = (
            recommendation not in {'', 'observe', 'normal'}
            or congestion in {'medium', 'high', 'severe'}
            or load in {'medium', 'high', 'overloaded'}
            or (link_util is not None and float(link_util) >= 0.70)
            or (latency is not None and float(latency) >= self.sla_target_ms * 0.75)
        )
        plan = self.build_plan() if should_recompute else None
        event = self._record_event(
            'context_auto_allocation',
            payload={
                'triggered': should_recompute,
                'recommendation': recommendation or None,
                'congestion': congestion or None,
                'load': load or None,
                'updates': updates,
                'plan': plan,
            },
        )
        return {'triggered': should_recompute, 'updates': updates, 'plan': plan, 'event': event}

    def apply_intent_feedback(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Translate Component 3 load-balance/resource intents into Component 1 actions."""
        intent_type = str(payload.get('type') or '').lower()
        intent_text = str(payload.get('intent') or '').lower()
        resource_keywords = {'load_balance', 'load-balancing', 'reroute', 'resource_allocation', 'optimize', 'scale'}
        should_recompute = intent_type in resource_keywords or any(keyword in intent_text for keyword in resource_keywords)
        route_result = None
        if intent_type in {'load_balance', 'reroute'} and payload.get('src_ip'):
            self._flow_sequence += 1
            route_result = self.route_request(
                client_ip=str(payload.get('src_ip')),
                client_port=46000 + (self._flow_sequence % 10000),
                vip_port=int(payload.get('dst_port') or 8000),
                ip_proto=6 if str(payload.get('proto') or 'tcp').lower() in {'tcp', '6'} else 17,
                request_size_kb=float((payload.get('metadata') or {}).get('request_size_kb', 128.0)),
                priority=int(payload.get('priority') or 100),
            )
        plan = self.build_plan() if should_recompute else None
        event = self._record_event(
            'intent_auto_allocation',
            payload={'triggered': should_recompute, 'intent_type': intent_type, 'route_result': route_result, 'plan': plan},
        )
        return {'triggered': should_recompute, 'route_result': route_result, 'plan': plan, 'event': event}

    def apply_security_feedback(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Let Component 4 security actions remove/release backend capacity automatically."""
        action = str(payload.get('action') or '').lower()
        subject = str(payload.get('subject') or '')
        backend = self._find_backend_by_subject(subject)
        if backend is None:
            event = self._record_event('security_auto_allocation_skipped', payload={'action': action, 'subject': subject})
            return {'triggered': False, 'backend': None, 'plan': None, 'event': event}

        if action in {'block', 'quarantine'}:
            health = self.set_backend_health(backend.name, False, f'security {action}: {payload.get("reason") or "policy"}')
            plan = self.build_plan()
            triggered = True
        elif action in {'release', 'allow'}:
            health = self.set_backend_health(backend.name, True, f'security {action}: {payload.get("reason") or "policy"}')
            plan = self.build_plan()
            triggered = True
        else:
            health = None
            plan = None
            triggered = False

        event = self._record_event(
            'security_auto_allocation',
            backend=backend.name,
            payload={'triggered': triggered, 'action': action, 'subject': subject, 'health': health, 'plan': plan},
        )
        return {'triggered': triggered, 'backend': backend.name, 'plan': plan, 'event': event}

    def route_request(
        self,
        client_ip: str,
        client_port: int,
        vip_port: int,
        ip_proto: int,
        request_size_kb: float = 128.0,
        priority: int = 100,
    ) -> Dict[str, Any]:
        self.total_requests += 1
        flow = (client_ip, int(client_port), int(vip_port), int(ip_proto))
        blocked = self._eligibility_report()
        backend = self.lb.choose_backend(flow)
        if backend is None:
            self.failed_requests += 1
            event = self._record_event(
                'route_failed',
                payload={'client_ip': client_ip, 'client_port': client_port, 'vip_port': vip_port, 'blocked': blocked},
            )
            return {'accepted': False, 'error': 'no eligible backend', 'blocked': blocked, 'event': event}

        self.rr_decisions += 1
        latency = self._estimate_latency_ms(backend, request_size_kb)
        if latency > self.sla_target_ms:
            self.sla_violations += 1

        self._flow_sequence += 1
        flow_rule = {
            'id': f'c1-flow-{self._flow_sequence:05d}',
            'client_ip': client_ip,
            'client_port': int(client_port),
            'vip_ip': self.lb.vip.ip,
            'vip_port': int(vip_port),
            'ip_proto': int(ip_proto),
            'backend_name': backend.name,
            'backend_ip': backend.ip,
            'backend_mac': backend.mac,
            'dpid': backend.dpid,
            'egress_port': backend.port,
            'priority': int(priority),
            'idle_timeout_sec': self.config.controller.flow_idle_timeout,
            'hard_timeout_sec': self.config.controller.flow_hard_timeout,
            'action': 'set_dst_and_forward',
            'algorithm': self.config.hybrid.rr.mode,
            'estimated_latency_ms': latency,
            'installed': True,
            'created_at': time.time(),
        }
        self.flow_rules.append(flow_rule)
        self.flow_rules = self.flow_rules[-120:]
        event = self._record_event('rr_route', backend=backend.name, payload=flow_rule)
        return {
            'accepted': True,
            'algorithm': self.config.hybrid.rr.mode,
            'backend': backend.as_dict(),
            'flow_rule': flow_rule,
            'conflict_resolution': blocked,
            'sla': self._sla_summary(),
            'event': event,
        }

    def simulate_workload(
        self,
        requests: int,
        clients: List[str],
        start_port: int,
        vip_port: int,
        request_size_kb: float,
        recompute_after: bool = True,
        inject_fault_backend: str | None = None,
    ) -> Dict[str, Any]:
        if inject_fault_backend:
            self.set_backend_health(inject_fault_backend, False, 'fault-tolerance simulation')

        distribution: Dict[str, int] = {}
        failures = 0
        routed: List[Dict[str, Any]] = []
        safe_clients = clients or ['10.0.0.1']
        for idx in range(int(requests)):
            client = safe_clients[idx % len(safe_clients)]
            result = self.route_request(
                client_ip=client,
                client_port=start_port + idx,
                vip_port=vip_port,
                ip_proto=6,
                request_size_kb=request_size_kb,
                priority=100,
            )
            if result.get('accepted'):
                backend_name = result['backend']['name']
                distribution[backend_name] = distribution.get(backend_name, 0) + 1
                routed.append(result['flow_rule'])
            else:
                failures += 1

        plan = self.build_plan() if recompute_after else None
        summary = {
            'requests': requests,
            'routed': len(routed),
            'failures': failures,
            'distribution': distribution,
            'latest_plan': plan,
            'sla': self._sla_summary(),
            'backends': self.backend_summary(),
            'recent_flows': routed[-12:],
        }
        self._record_event('workload_simulation', payload=summary)
        return summary

    def component_status(self) -> Dict[str, Any]:
        runtime = self.lb.status()
        return {
            'component': {
                'number': 1,
                'name': 'Hybrid Load Balancing Algorithm for SDN-Based Cloud Resource Allocation',
                'algorithm': 'Round Robin for real-time routing plus Genetic Algorithm for long-term resource optimization',
                'features': [
                    'real-time RR/SWRR backend selection',
                    'GA resource-weight recomputation',
                    'RR-vs-GA conflict handling with overload gating',
                    'flow-rule generation for SDN switches',
                    'backend metric and port-stat ingestion',
                    'fault tolerance through backend health exclusion',
                    'SLA compliance tracking',
                ],
            },
            'vip': runtime['vip'],
            'controller': runtime['controller'],
            'weights': runtime['weights'],
            'backends': runtime['backends'],
            'active_flows': runtime['active_flows'],
            'flow_rules': self.flow_rules[-30:],
            'events': self.events[-30:],
            'metrics': {
                'total_requests': self.total_requests,
                'failed_requests': self.failed_requests,
                'rr_decisions': self.rr_decisions,
                'ga_runs': self.ga_runs,
                'healthy_backends': sum(1 for backend in self.lb.backends if backend.healthy),
                'total_backends': len(self.lb.backends),
            },
            'sla': self._sla_summary(),
        }

    def reset_runtime(self) -> Dict[str, Any]:
        self.lb = HybridLoadBalancer(self.config)
        self.flow_rules.clear()
        self.events.clear()
        self.total_requests = 0
        self.failed_requests = 0
        self.rr_decisions = 0
        self.ga_runs = 0
        self.sla_violations = 0
        self._flow_sequence = 0
        self._record_event('runtime_reset')
        return self.component_status()

    def _record_event(self, event_type: str, backend: str | None = None, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        event = {
            'type': event_type,
            'backend': backend,
            'payload': payload or {},
            'ts': time.time(),
        }
        self.events.append(event)
        self.events = self.events[-160:]
        return event

    def _sla_summary(self) -> Dict[str, Any]:
        evaluated = max(0, self.total_requests - self.failed_requests)
        compliant = max(0, evaluated - self.sla_violations)
        compliance = (compliant / evaluated * 100.0) if evaluated else 100.0
        return {
            'target_latency_ms': self.sla_target_ms,
            'evaluated_requests': evaluated,
            'violations': self.sla_violations,
            'compliance_percent': round(compliance, 2),
        }

    def _estimate_latency_ms(self, backend: Any, request_size_kb: float) -> float:
        metrics = backend.metrics
        base_latency = metrics.latency_ms if metrics.latency_ms is not None else 24.0
        cpu = metrics.cpu_util if metrics.cpu_util is not None else 0.20
        mem = metrics.mem_util if metrics.mem_util is not None else 0.20
        bw = metrics.bw_util if metrics.bw_util is not None else 0.10
        pressure = max(cpu, mem, bw)
        conn_penalty = min(80.0, metrics.active_connections * 1.8)
        payload_penalty = min(35.0, request_size_kb / 128.0)
        return round(base_latency * (1.0 + pressure) + conn_penalty + payload_penalty, 2)

    def _eligibility_report(self) -> List[Dict[str, Any]]:
        report: List[Dict[str, Any]] = []
        thresholds = self.config.hybrid.overload_threshold
        for backend in self.lb.backends:
            reasons: List[str] = []
            metrics = backend.metrics
            if not backend.healthy:
                reasons.append('unhealthy')
            if metrics.cpu_util is not None and metrics.cpu_util >= thresholds.cpu:
                reasons.append('cpu_overload')
            if metrics.mem_util is not None and metrics.mem_util >= thresholds.mem:
                reasons.append('memory_overload')
            if metrics.bw_util is not None and metrics.bw_util >= thresholds.bw:
                reasons.append('bandwidth_overload')
            max_conn = max(1, int(getattr(backend.capacity, 'max_connections', 100) or 100))
            if metrics.active_connections / max_conn >= thresholds.conn:
                reasons.append('connection_overload')
            report.append({
                'backend': backend.name,
                'eligible': not reasons,
                'reasons': reasons,
            })
        return report

    def _find_backend_by_subject(self, subject: str) -> Any:
        for backend in self.lb.backends:
            if subject in {backend.name, backend.ip, backend.mac}:
                return backend
        return None
