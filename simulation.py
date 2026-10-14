"""
simulation.py
--------------
Turns the static graph + combinatorial bounds into an actual minute-by-minute
evacuation schedule, and re-plans live when a corridor fails mid-run.

Pipeline used here (each step is a different piece of discrete math):

  1. plan_routes()        Dijkstra: each room's fastest route to an ALLOWED,
                           reachable exit; the route's bottleneck rate is the
                           minimum corridor capacity along it.
  2. build_conflict_graph()  two rooms conflict iff their routes share a
                           corridor -- this is the graph coloring INPUT.
  3. greedy_coloring()     Unit 6: colors = evacuation WAVES. Rooms sharing a
                           color never share a corridor, so a wave can safely
                           run "all at once" without collision.
  4. run_simulation()      Unit 4: total time is the recurrence
                                T(0) = 0
                                T(k) = T(k-1) + (time for wave k to clear)
                           advanced tick-by-tick so a scheduled event (a new
                           block) can interrupt and trigger a local re-plan.
"""

import math
from algorithms import dijkstra, reconstruct_path, greedy_coloring


def plan_routes(graph, rooms, allowed_exits):
    """For every room: best (fastest) route to one of its allowed, reachable exits."""
    routes = {}
    stranded = []
    for room in rooms:
        dist, prev = dijkstra(graph, room)
        candidates = [(dist[e], e) for e in allowed_exits[room] if dist.get(e, math.inf) < math.inf]
        if not candidates:
            stranded.append(room)
            continue
        eta, best_exit = min(candidates)
        path = reconstruct_path(prev, room, best_exit)
        edge_set = frozenset(frozenset((path[i], path[i + 1])) for i in range(len(path) - 1))
        bottleneck = min(graph.adj[path[i]][path[i + 1]]["capacity"] for i in range(len(path) - 1))
        routes[room] = {"exit": best_exit, "path": path, "eta": eta,
                         "edges": edge_set, "bottleneck": bottleneck}
    return routes, stranded


def build_conflict_graph(routes):
    """Two rooms conflict iff their planned routes share at least one corridor."""
    rooms = list(routes)
    conflict = {r: set() for r in rooms}
    for i in range(len(rooms)):
        for j in range(i + 1, len(rooms)):
            r1, r2 = rooms[i], rooms[j]
            if routes[r1]["edges"] & routes[r2]["edges"]:
                conflict[r1].add(r2)
                conflict[r2].add(r1)
    return conflict


def waves_from_coloring(routes):
    conflict = build_conflict_graph(routes)
    color = greedy_coloring(conflict)
    waves = {}
    for room, c in color.items():
        waves.setdefault(c, []).append(room)
    return waves, conflict, len(set(color.values()))


def run_simulation(graph, population, allowed_exits, events, log=None):
    """
    Runs waves sequentially. Inside a wave, rooms move in parallel (no
    corridor collisions, guaranteed by the coloring). A scheduled event
    (e.g. a new block) can fire on any tick and triggers a LOCAL re-plan
    for whichever active room's route it broke -- the rest of the wave
    is undisturbed, which is the "commit only what's already moving"
    rule described in the project report.
    """
    remaining = dict(population)
    routes, stranded = plan_routes(graph, list(population), allowed_exits)
    waves, conflict, n_waves = waves_from_coloring(routes)
    events = sorted(events)
    t = 0
    completion_tick = {}
    history = []  # (tick, wave, {room: remaining})

    for wave_id in sorted(waves):
        members = [r for r in waves[wave_id] if remaining[r] > 0]
        while any(remaining[r] > 0 for r in members):
            t += 1
            # --- apply any event scheduled for this exact tick ---
            while events and events[0][0] == t:
                _, (action, u, v) = events.pop(0)
                if action == "block":
                    graph.block(u, v)
                    if log:
                        log(t, f"corridor {u}-{v} BLOCKED -- re-planning affected rooms")
                    for r in members:
                        if remaining[r] > 0 and frozenset((u, v)) in routes[r]["edges"]:
                            dist, prev = dijkstra(graph, r)
                            cands = [(dist[e], e) for e in allowed_exits[r] if dist.get(e, math.inf) < math.inf]
                            if not cands:
                                if log:
                                    log(t, f"room {r} has NO remaining route -- stranded!")
                                continue
                            eta, best_exit = min(cands)
                            path = reconstruct_path(prev, r, best_exit)
                            edges = frozenset(frozenset((path[i], path[i + 1])) for i in range(len(path) - 1))
                            bneck = min(graph.adj[path[i]][path[i + 1]]["capacity"] for i in range(len(path) - 1))
                            routes[r] = {"exit": best_exit, "path": path, "eta": eta,
                                         "edges": edges, "bottleneck": bneck}
                            if log:
                                log(t, f"room {r} re-routed -> {'->'.join(path)} "
                                    f"(new rate {bneck}/min)")

            # --- move people for this tick ---
            for r in members:
                if remaining[r] > 0:
                    rate = routes[r]["bottleneck"]
                    depart = min(remaining[r], rate)
                    remaining[r] -= depart
                    if remaining[r] == 0:
                        completion_tick[r] = t
            history.append((t, wave_id, dict(remaining)))

    total_time = max(completion_tick.values()) if completion_tick else 0
    return {
        "routes": routes,
        "waves": waves,
        "n_waves": n_waves,
        "conflict": conflict,
        "completion_tick": completion_tick,
        "total_time": total_time,
        "history": history,
        "stranded": stranded,
    }
