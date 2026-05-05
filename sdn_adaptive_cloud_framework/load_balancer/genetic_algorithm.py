"""Genetic Algorithm for periodic server-order optimisation (Module 4)."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Sequence

from .server_monitor import ServerStatus


@dataclass
class GAConfig:
    population_size: int = 20
    generations: int = 30
    elite_fraction: float = 0.2
    mutation_rate: float = 0.1
    crossover_rate: float = 0.7
    seed: int | None = None


def _fitness(order: Sequence[int], servers: Sequence[ServerStatus]) -> float:
    """Lower load early in the order = higher fitness.

    ``score = sum(load_score / position)`` so the first position carries the
    most weight.  We negate to convert to fitness.
    """
    total = 0.0
    for position, idx in enumerate(order, start=1):
        total += servers[idx].load_score() / position
    return -total


def _crossover(a: List[int], b: List[int], rng: random.Random) -> List[int]:
    if len(a) <= 2:
        return list(a)
    cut1 = rng.randint(1, len(a) - 2)
    cut2 = rng.randint(cut1, len(a) - 1)
    middle = a[cut1:cut2]
    rest = [g for g in b if g not in middle]
    return rest[:cut1] + middle + rest[cut1:]


def _mutate(order: List[int], rng: random.Random) -> List[int]:
    if len(order) < 2:
        return order
    i, j = rng.sample(range(len(order)), 2)
    order[i], order[j] = order[j], order[i]
    return order


def optimise_server_order(
    servers: Sequence[ServerStatus],
    config: GAConfig | None = None,
) -> List[ServerStatus]:
    """Return ``servers`` reordered so the most-preferred backend is first."""
    config = config or GAConfig()
    rng = random.Random(config.seed)
    n = len(servers)
    if n <= 1:
        return list(servers)

    base = list(range(n))
    population: List[List[int]] = []
    for _ in range(config.population_size):
        candidate = base.copy()
        rng.shuffle(candidate)
        population.append(candidate)

    elite_count = max(1, int(config.elite_fraction * config.population_size))
    for _ in range(config.generations):
        scored = [(o, _fitness(o, servers)) for o in population]
        scored.sort(key=lambda x: x[1], reverse=True)
        next_pop = [list(scored[i][0]) for i in range(elite_count)]
        while len(next_pop) < config.population_size:
            parent_a = rng.choice(scored[:elite_count])[0]
            parent_b = rng.choice(scored)[0]
            if rng.random() < config.crossover_rate:
                child = _crossover(parent_a, parent_b, rng)
            else:
                child = list(parent_a)
            if rng.random() < config.mutation_rate:
                child = _mutate(child, rng)
            next_pop.append(child)
        population = next_pop

    best = max(population, key=lambda o: _fitness(o, servers))
    return [servers[i] for i in best]


__all__ = ["GAConfig", "optimise_server_order"]
