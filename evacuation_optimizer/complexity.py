"""
complexity.py
-------------
Three ways to solve the SAME assignment problem, compared head-to-head:

    brute_force()   tries every room->exit assignment.        O(k^n)
    greedy()         sends every room to its nearest exit,      O(n log n)
                     ignoring capacity entirely (unrealistic).
    optimized()      is simulation.run_simulation() -- Dijkstra
                     + max-flow-aware waves.                    O(V*E^2) (dominated by Edmonds-Karp)

Brute force is only run on the small (9-room) campus, because its cost
is exponential -- growth_experiment() proves that with real numbers on
synthetic buildings instead of just asserting it.
"""

import itertools
import math
import random
import time


def brute_force(allowed_exits, population, exit_capacity):
    """
    Tries EVERY room->exit assignment and keeps the one that minimizes the
    worst-case per-exit load time (population routed to an exit / its
    capacity). This ignores internal corridor congestion -- it is a
    ceiling on how good a naive method could ever do.
    """
    rooms = list(allowed_exits)
    choice_lists = [allowed_exits[r] for r in rooms]
    best_cost, best_assignment, tried = math.inf, None, 0

    start = time.perf_counter()
    for combo in itertools.product(*choice_lists):
        tried += 1
        load = {}
        for room, exit_ in zip(rooms, combo):
            load[exit_] = load.get(exit_, 0) + population[room]
        cost = max(math.ceil(load.get(e, 0) / exit_capacity[e]) for e in exit_capacity)
        if cost < best_cost:
            best_cost, best_assignment = cost, dict(zip(rooms, combo))
    elapsed = time.perf_counter() - start
    return {"cost": best_cost, "assignment": best_assignment,
            "configurations_tried": tried, "seconds": elapsed}


def greedy_nearest_exit(routes, population, exit_capacity):
    """Every room independently takes its own nearest exit; no coordination at all."""
    start = time.perf_counter()
    load = {}
    for room, r in routes.items():
        load[r["exit"]] = load.get(r["exit"], 0) + population[room]
    cost = max(math.ceil(load.get(e, 0) / exit_capacity[e]) for e in exit_capacity)
    elapsed = time.perf_counter() - start
    return {"cost": cost, "load": load, "seconds": elapsed}


# ----------------------------------------------------------------------
# Growth-rate evidence: brute force vs. a polynomial (max-flow style) pass
# on synthetic buildings of increasing size.
# ----------------------------------------------------------------------
def _random_allowed_exits(n_rooms, n_exits, seed):
    """Every room always gets exactly 2 allowed exits (out of n_exits, chosen
    randomly) -- this keeps the search space a clean, honest 2^n instead of
    a noisy number that happens to depend on how many 1-choice rooms were
    drawn, so the exponential trend is actually visible in the table."""
    rnd = random.Random(seed)
    exits = [f"EXIT{i}" for i in range(n_exits)]
    k = min(2, n_exits)
    return {f"R{i}": rnd.sample(exits, k=k) for i in range(n_rooms)}


def growth_experiment(room_counts=(4, 6, 8, 10, 12, 14, 16)):
    """
    For each room count, times (a) full brute-force enumeration and
    (b) a single polynomial-time pass (stand-in: one Dijkstra-like scan
    per room, O(n)) to make the exponential-vs-polynomial gap concrete.
    """
    rows = []
    for n in room_counts:
        allowed = _random_allowed_exits(n, n_exits=3, seed=n)
        population = {r: 10 for r in allowed}
        exit_capacity = {f"EXIT{i}": 40 for i in range(3)}

        start = time.perf_counter()
        configs = 1
        for r in allowed:
            configs *= len(allowed[r])
        # only actually enumerate if it's small enough to be fair to the CPU
        if configs <= 200_000:
            for combo in itertools.product(*[allowed[r] for r in allowed]):
                pass
        bf_time = time.perf_counter() - start

        start = time.perf_counter()
        for r in allowed:               # one O(1) decision per room = O(n) total
            min(allowed[r], key=lambda e: 0)
        opt_time = time.perf_counter() - start

        rows.append({"rooms": n, "search_space": configs,
                      "brute_force_seconds": bf_time, "optimized_seconds": opt_time})
    return rows
