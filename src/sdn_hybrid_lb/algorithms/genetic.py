from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple
import math
import random
import statistics
import time

from sdn_hybrid_lb.utils.models import BackendServer


def _normalize(vec: List[float]) -> List[float]:
    s = sum(max(0.0, v) for v in vec)
    if s <= 0.0:
        return [1.0 / len(vec) for _ in vec]
    return [max(0.0, v) / s for v in vec]


@dataclass
class GAParams:
    population: int = 30
    generations: int = 40
    crossover_rate: float = 0.7
    mutation_rate: float = 0.2
    tournament_k: int = 3
    elitism: int = 2
    seed: int = 42


@dataclass
class FitnessParams:
    # weights to aggregate utilization
    w_cpu: float = 0.40
    w_mem: float = 0.30
    w_bw: float = 0.20
    w_conn: float = 0.10

    overload_threshold: float = 0.85
    penalty_overload: float = 3.0
    penalty_variance: float = 1.0

    sla_latency_ms: float = 200.0
    penalty_sla: float = 5.0


class GeneticOptimizer:
    """GA that outputs a weight distribution over backends.

    Individual representation: vector w (len=N) with w_i >= 0 and sum(w)=1.
    """

    def __init__(self, ga: GAParams, fit: FitnessParams) -> None:
        self.ga = ga
        self.fit = fit
        self._rng = random.Random(ga.seed)

    def optimize(self, backends: Sequence[BackendServer]) -> Dict[str, float]:
        if not backends:
            return {}

        names = [b.name for b in backends]
        n = len(backends)

        # Snapshot metrics (avoid changing during GA loop)
        util = self._util_vector(backends)

        # Build population
        pop = [self._random_dirichlet(n) for _ in range(self.ga.population)]

        def fitness(ind: List[float]) -> float:
            return self._fitness(ind, util, backends)

        # Evolution
        for _gen in range(self.ga.generations):
            scored = sorted(((fitness(ind), ind) for ind in pop), key=lambda x: x[0], reverse=True)

            # Elitism
            new_pop: List[List[float]] = [scored[i][1][:] for i in range(min(self.ga.elitism, len(scored)))]

            while len(new_pop) < self.ga.population:
                p1 = self._tournament_select(scored)
                p2 = self._tournament_select(scored)

                c1, c2 = p1[:], p2[:]
                if self._rng.random() < self.ga.crossover_rate:
                    c1, c2 = self._blend_crossover(p1, p2)

                self._mutate(c1)
                self._mutate(c2)

                new_pop.append(c1)
                if len(new_pop) < self.ga.population:
                    new_pop.append(c2)

            pop = new_pop

        # Return best
        best = max(pop, key=lambda ind: self._fitness(ind, util, backends))
        best = _normalize(best)
        return {names[i]: float(best[i]) for i in range(n)}

    # ---------- Internals ----------

    def _random_dirichlet(self, n: int) -> List[float]:
        # Gamma(1,1) samples -> normalize
        vec = [self._rng.random() + 1e-9 for _ in range(n)]
        return _normalize(vec)

    def _tournament_select(self, scored: List[Tuple[float, List[float]]]) -> List[float]:
        k = max(2, int(self.ga.tournament_k))
        cand = [scored[self._rng.randrange(0, len(scored))] for _ in range(k)]
        cand.sort(key=lambda x: x[0], reverse=True)
        return cand[0][1]

    def _blend_crossover(self, p1: List[float], p2: List[float], alpha: float = 0.5) -> Tuple[List[float], List[float]]:
        # BLX-alpha style blending
        n = len(p1)
        c1 = []
        c2 = []
        for i in range(n):
            a = p1[i]
            b = p2[i]
            lo = min(a, b) - alpha * abs(a - b)
            hi = max(a, b) + alpha * abs(a - b)
            c1.append(self._rng.uniform(lo, hi))
            c2.append(self._rng.uniform(lo, hi))
        return _normalize(c1), _normalize(c2)

    def _mutate(self, ind: List[float]) -> None:
        n = len(ind)
        for i in range(n):
            if self._rng.random() < self.ga.mutation_rate:
                # Small Gaussian perturbation
                ind[i] += self._rng.gauss(0.0, 0.08)
        # keep non-negative + sum=1
        for i in range(n):
            if ind[i] < 0.0:
                ind[i] = 0.0
        norm = _normalize(ind)
        ind[:] = norm

    def _util_vector(self, backends: Sequence[BackendServer]) -> List[float]:
        # Convert metrics into a single normalized utilization per backend.
        # Missing values become 0.0 (unknown -> treated as idle), which is conservative
        # for optimization but safe because overload gating is enforced elsewhere.
        conns = [b.metrics.active_connections for b in backends]
        max_conn = max(conns) if conns else 1

        u = []
        for b in backends:
            cpu = b.metrics.cpu_util if b.metrics.cpu_util is not None else 0.0
            mem = b.metrics.mem_util if b.metrics.mem_util is not None else 0.0
            bw = b.metrics.bw_util if b.metrics.bw_util is not None else 0.0
            conn = (b.metrics.active_connections / max_conn) if max_conn > 0 else 0.0
            util = (
                self.fit.w_cpu * cpu
                + self.fit.w_mem * mem
                + self.fit.w_bw * bw
                + self.fit.w_conn * conn
            )
            # clamp
            util = max(0.0, min(1.0, util))
            u.append(util)
        return u

    def _fitness(self, ind: List[float], util: List[float], backends: Sequence[BackendServer]) -> float:
        # Predicted utilization: current util + demand_scale * assigned_weight
        demand_scale = 0.35
        pred = [min(1.0, util[i] + demand_scale * ind[i]) for i in range(len(ind))]

        avg = sum(pred) / len(pred)
        var = sum((x - avg) ** 2 for x in pred) / len(pred)

        # Overload penalty
        thr = self.fit.overload_threshold
        overload = sum(max(0.0, x - thr) ** 2 for x in pred)

        # SLA soft penalty: predicted weighted latency
        sla_ms = self.fit.sla_latency_ms
        latencies = []
        for i, b in enumerate(backends):
            base = b.metrics.latency_ms if b.metrics.latency_ms is not None else 10.0
            # Simple convex latency model:
            #   latency grows rapidly as utilization approaches 1
            eps = 1e-6
            factor = 1.0 + (pred[i] / max(eps, (1.0 - pred[i])))
            latencies.append(base * factor)
        weighted_latency = sum(ind[i] * latencies[i] for i in range(len(ind)))
        sla_violation = max(0.0, (weighted_latency - sla_ms) / max(1.0, sla_ms))

        # Cost (lower is better)
        cost = avg
        cost += self.fit.penalty_variance * var
        cost += self.fit.penalty_overload * overload
        cost += self.fit.penalty_sla * sla_violation

        # Fitness (higher is better)
        return -cost
