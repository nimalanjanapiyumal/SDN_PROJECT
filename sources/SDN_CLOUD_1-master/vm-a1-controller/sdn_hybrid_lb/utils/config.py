from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import os


def _require_yaml() -> Any:
    try:
        import yaml  # type: ignore
        return yaml
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "PyYAML is required to load config files. Install with: pip install PyYAML"
        ) from e


@dataclass
class ControllerConfig:
    rest_api_port: int = 8080
    poll_interval_sec: float = 2.0
    ga_interval_sec: float = 10.0
    flow_idle_timeout: int = 30
    flow_hard_timeout: int = 0


@dataclass
class RyuStatsConfig:
    enabled: bool = True


@dataclass
class PrometheusConfig:
    enabled: bool = False
    base_url: str = "http://localhost:9090"
    timeout_sec: float = 2.0
    promql: Dict[str, str] = field(default_factory=dict)


@dataclass
class MonitoringConfig:
    ryu_stats: RyuStatsConfig = field(default_factory=RyuStatsConfig)
    prometheus: PrometheusConfig = field(default_factory=PrometheusConfig)
    instances: Dict[str, str] = field(default_factory=dict)  # backend_name -> instance label


@dataclass
class OverloadThresholds:
    cpu: float = 0.85
    mem: float = 0.85
    bw: float = 0.85
    conn: float = 0.90


@dataclass
class RRConfig:
    mode: str = "smooth_weighted"  # "round_robin" | "smooth_weighted"


@dataclass
class FitnessWeights:
    cpu: float = 0.40
    mem: float = 0.30
    bw: float = 0.20
    conn: float = 0.10


@dataclass
class FitnessConfig:
    util_weights: FitnessWeights = field(default_factory=FitnessWeights)
    overload_threshold: float = 0.85
    penalty_overload: float = 3.0
    penalty_variance: float = 1.0
    sla_latency_ms: float = 200.0
    penalty_sla: float = 5.0


@dataclass
class GAConfig:
    population: int = 30
    generations: int = 40
    crossover_rate: float = 0.7
    mutation_rate: float = 0.2
    tournament_k: int = 3
    elitism: int = 2
    seed: int = 42
    fitness: FitnessConfig = field(default_factory=FitnessConfig)


@dataclass
class HybridConfig:
    overload_threshold: OverloadThresholds = field(default_factory=OverloadThresholds)
    rr: RRConfig = field(default_factory=RRConfig)
    ga: GAConfig = field(default_factory=GAConfig)


@dataclass
class AppConfig:
    controller: ControllerConfig = field(default_factory=ControllerConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    hybrid: HybridConfig = field(default_factory=HybridConfig)
    vip: Dict[str, Any] = field(default_factory=dict)
    backends: List[Dict[str, Any]] = field(default_factory=list)
    clients: List[Dict[str, Any]] = field(default_factory=list)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "AppConfig":
        # Controller
        c = d.get("controller", {}) or {}
        controller = ControllerConfig(
            rest_api_port=int(c.get("rest_api_port", 8080)),
            poll_interval_sec=float(c.get("poll_interval_sec", 2.0)),
            ga_interval_sec=float(c.get("ga_interval_sec", 10.0)),
            flow_idle_timeout=int(c.get("flow_idle_timeout", 30)),
            flow_hard_timeout=int(c.get("flow_hard_timeout", 0)),
        )

        # Monitoring
        m = d.get("monitoring", {}) or {}
        ryu_stats = RyuStatsConfig(enabled=bool((m.get("ryu_stats") or {}).get("enabled", True)))

        p = (m.get("prometheus") or {})
        prom = PrometheusConfig(
            enabled=bool(p.get("enabled", False)),
            base_url=str(p.get("base_url", "http://localhost:9090")),
            timeout_sec=float(p.get("timeout_sec", 2.0)),
            promql=dict(p.get("promql", {}) or {}),
        )
        monitoring = MonitoringConfig(
            ryu_stats=ryu_stats,
            prometheus=prom,
            instances=dict(m.get("instances", {}) or {}),
        )

        # Hybrid
        h = d.get("hybrid", {}) or {}
        ot = h.get("overload_threshold", {}) or {}
        overload = OverloadThresholds(
            cpu=float(ot.get("cpu", 0.85)),
            mem=float(ot.get("mem", 0.85)),
            bw=float(ot.get("bw", 0.85)),
            conn=float(ot.get("conn", 0.90)),
        )

        rr = RRConfig(mode=str((h.get("rr") or {}).get("mode", "smooth_weighted")))

        g = h.get("ga", {}) or {}
        fw = ((g.get("fitness") or {}).get("util_weights") or {})
        fitness_weights = FitnessWeights(
            cpu=float(fw.get("cpu", 0.40)),
            mem=float(fw.get("mem", 0.30)),
            bw=float(fw.get("bw", 0.20)),
            conn=float(fw.get("conn", 0.10)),
        )
        gf = g.get("fitness", {}) or {}
        fitness = FitnessConfig(
            util_weights=fitness_weights,
            overload_threshold=float(gf.get("overload_threshold", 0.85)),
            penalty_overload=float(gf.get("penalty_overload", 3.0)),
            penalty_variance=float(gf.get("penalty_variance", 1.0)),
            sla_latency_ms=float(gf.get("sla_latency_ms", 200.0)),
            penalty_sla=float(gf.get("penalty_sla", 5.0)),
        )

        ga = GAConfig(
            population=int(g.get("population", 30)),
            generations=int(g.get("generations", 40)),
            crossover_rate=float(g.get("crossover_rate", 0.7)),
            mutation_rate=float(g.get("mutation_rate", 0.2)),
            tournament_k=int(g.get("tournament_k", 3)),
            elitism=int(g.get("elitism", 2)),
            seed=int(g.get("seed", 42)),
            fitness=fitness,
        )

        hybrid = HybridConfig(overload_threshold=overload, rr=rr, ga=ga)

        return AppConfig(
            controller=controller,
            monitoring=monitoring,
            hybrid=hybrid,
            vip=dict(d.get("vip", {}) or {}),
            backends=list(d.get("backends", []) or []),
            clients=list(d.get("clients", []) or []),
        )


def load_config(path: Optional[str] = None) -> AppConfig:
    config_path = path or os.environ.get("SDN_HYBRID_LB_CONFIG") or "config.yaml"
    yaml = _require_yaml()
    with open(config_path, "r", encoding="utf-8") as f:
        d = yaml.safe_load(f) or {}
    return AppConfig.from_dict(d)
