"""
main.py
-------
Runs the full pipeline on a scenario that is NOT fixed at import time --
scenario.choose_scenario() lets you pick the report's sample campus, type
in your own building at the terminal, or generate a random one. Everything
downstream (combinatorics, max-flow, matching, coloring, simulation) reads
from whatever was chosen. After the analytical report, you can replay the
evacuation as a colourised live terminal animation and export a PNG.
"""

import math
from algorithms import (
    edmonds_karp, bipartite_matching, hall_deficiency_witness,
    edge_disjoint_connectivity,
)
from combinatorics import (
    count_configurations, pigeonhole_time_bound, maxflow_time_bound,
    generalized_pigeonhole_bound, inclusion_exclusion_exit_access,
    inclusion_exclusion_union_count,
)
from advanced_networks import (
    min_cost_exit_assignment, time_expanded_evacuation_bound,
)
from simulation import plan_routes, waves_from_coloring, run_simulation
from complexity import brute_force, greedy_nearest_exit, growth_experiment
import scenario as scenario_mod
import animate
import visualize
from graph import Graph


def header(title):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def yes(prompt, default="y"):
    ans = input(f"{prompt} [{'Y/n' if default=='y' else 'y/N'}]: ").strip().lower()
    if not ans:
        return default == "y"
    return ans.startswith("y")


def rebuild_graph(sc):
    """Fresh, unblocked-by-events copy of the scenario's graph (events get
    replayed live during simulation instead of being pre-applied twice)."""
    g2 = Graph()
    for u, v, d in sc["graph"].edges():
        g2.add_edge(u, v, weight=d["weight"], capacity=d["capacity"])
        if d["blocked"]:
            g2.block(u, v)
    return g2


def main():
    sc = scenario_mod.choose_scenario()
    ROOMS, EXITS = sc["rooms"], sc["exits"]
    POPULATION, EXIT_CAPACITY = sc["population"], sc["exit_capacity"]
    ALLOWED_EXITS, MARSHALS, EVENTS = sc["allowed_exits"], sc["marshals"], sc["events"]
    total_people = sum(POPULATION.values())

    header(f"RUNNING: {sc['label']}")
    print(f"Rooms: {ROOMS}\nExits: {EXITS}  capacities={EXIT_CAPACITY}")
    print(f"Population: {POPULATION}  -> total = {total_people}")
    print(f"Allowed exits: {ALLOWED_EXITS}")
    print(f"Scheduled live events: {EVENTS if EVENTS else '(none)'}")

    # =====================================================================
    header("1. BUILDING MODEL  (Unit 6: graphs, degree, connectivity)")
    # =====================================================================
    g = rebuild_graph(sc)
    for n in sorted(g.nodes):
        print(f"  deg({n}) = {g.degree(n)}")
    print(f"\nReachability from {ROOMS[0]}: {g.is_connected(ROOMS[0], EXITS)}")
    print("Edge-disjoint route resilience from the first room:")
    for exit_node in EXITS:
        path_count, cut_edges = edge_disjoint_connectivity(g, ROOMS[0], exit_node)
        print(f"  {ROOMS[0]} -> {exit_node}: {path_count} edge-disjoint path(s); "
              f"minimum corridor cut={cut_edges}")

    # =====================================================================
    header("2. COMBINATORICS  (Unit 2 & 3: counting, pigeonhole)")
    # =====================================================================
    total_configs, per_room = count_configurations(ALLOWED_EXITS)
    print(f"Per-room exit choices: {per_room}")
    print(f"Multiplication principle -> {' x '.join(str(v) for v in per_room.values())} "
          f"= {total_configs} configurations")
    print(f"Generalized pigeonhole: assigning {total_people} people across {len(EXITS)} exits "
          f"forces at least {generalized_pigeonhole_bound(total_people, len(EXITS))} "
          f"people at one exit.")

    naive_bound, total_cap = pigeonhole_time_bound(total_people, EXIT_CAPACITY)
    print(f"\nPigeonhole bound: {total_people} people, {total_cap}/min combined exit capacity.")
    print(f"No schedule can beat ceil({total_people}/{total_cap}) = {naive_bound} minutes.")

    access_sets = [
        {room for room, allowed in ALLOWED_EXITS.items() if exit_node in allowed}
        for exit_node in EXITS
    ]
    union_count, _ = inclusion_exclusion_union_count(access_sets)
    print(f"Inclusion-Exclusion across {len(EXITS)} exit-access sets: "
          f"{union_count} rooms can use at least one allowed exit.")
    if len(EXITS) == 2:
        ie = inclusion_exclusion_exit_access(ALLOWED_EXITS, EXITS)
        u, chk = ie["union_check"]
        print(f"  Two-exit check: |union|={u} directly, {chk} by |A|+|B|-|A intersect B|.")

    # =====================================================================
    header("3. MAX-FLOW  (relaxed one-tick throughput upper bound)")
    # =====================================================================
    flow_g = rebuild_graph(sc)
    for r in ROOMS:
        flow_g.add_edge("SOURCE", r, weight=0, capacity=POPULATION[r])
    for e in EXITS:
        flow_g.add_edge(e, "SINK", weight=0, capacity=EXIT_CAPACITY[e])

    max_flow, trace, cut_edges = edmonds_karp(flow_g, "SOURCE", "SINK")
    print(f"Relaxed network throughput bound: {max_flow} people/min "
          "(room supplies limited; all exits treated as eligible)")
    for path, bn in trace:
        print(f"  {' -> '.join(path):45s} +{bn}/min")
    print(f"Min-cut (true bottleneck): {cut_edges}")

    tight_bound = maxflow_time_bound(total_people, max_flow) if max_flow > 0 else float("inf")
    print(f"\nMax-flow-based lower bound: {tight_bound} minutes "
          f"(>= naive pigeonhole {naive_bound})")

    # =====================================================================
    header("4. EXTENDED NETWORK MODELS (time expansion + min-cost flow)")
    # =====================================================================
    expanded = time_expanded_evacuation_bound(
        rebuild_graph(sc), POPULATION, EXITS, EXIT_CAPACITY)
    if expanded["complete"]:
        print(f"Time-expanded optimistic lower bound: {expanded['minimum_ticks']} ticks "
              f"for {expanded['evacuated']}/{expanded['total_people']} people.")
    else:
        print(f"Time-expanded model carried {expanded['evacuated']}/"
              f"{expanded['total_people']} people within its horizon; complete evacuation "
              "was not established.")
    print("  Assumption: all rooms may use all exits; this is not a policy-valid schedule.")

    allocation_horizon = expanded["minimum_ticks"] if expanded["complete"] else max(1, naive_bound)
    allocation = min_cost_exit_assignment(
        rebuild_graph(sc), POPULATION, ALLOWED_EXITS, EXITS,
        EXIT_CAPACITY, allocation_horizon)
    print(f"Min-cost exit assignment over {allocation_horizon} tick(s): "
          f"{allocation['evacuated']}/{total_people} people assigned; "
          f"total modeled travel cost={allocation['total_cost']}.")
    print("  This assignment respects allowed exits and exit capacities, but omits "
          "shared corridor-capacity scheduling.")

    # =====================================================================
    header("5. BIPARTITE MATCHING  (Unit 6: Kuhn's algorithm, Hall's theorem)")
    # =====================================================================
    match_right = {}
    if MARSHALS:
        room_to_marshals = {
            room: [marshal for marshal, assigned_rooms in MARSHALS.items()
                   if room in assigned_rooms]
            for room in ROOMS
        }
        match_right, unmatched = bipartite_matching(ROOMS, room_to_marshals)
        for marshal, room in match_right.items():
            print(f"  {marshal} covers {room}")
        covered = set(match_right.values())
        uncovered = [r for r in ROOMS if r not in covered]
        print(f"\nMax matching: {len(match_right)}/{len(ROOMS)} rooms covered. Uncovered: {uncovered}")
        if unmatched:
            witness, nbhd = hall_deficiency_witness(
                ROOMS, room_to_marshals, match_right)
            print(f"Hall's theorem witness on room side: S={sorted(witness)}, "
                  f"N(S)={sorted(nbhd)}; |N(S)|={len(nbhd)}, |S|={len(witness)}.")
    else:
        print("(no marshal roster defined for this scenario -- skipping)")

    # =====================================================================
    header("6. ROUTE PLANNING + GRAPH COLORING  (Unit 6: Dijkstra, coloring)")
    # =====================================================================
    sim_graph = rebuild_graph(sc)
    routes, stranded = plan_routes(sim_graph, ROOMS, ALLOWED_EXITS)
    for r in ROOMS:
        if r in routes:
            rt = routes[r]
            print(f"  {r}: {'->'.join(rt['path']):30s} eta={rt['eta']} min  "
                  f"bottleneck={rt['bottleneck']}/min")
    if stranded:
        print(f"  STRANDED (no reachable allowed exit): {stranded}")

    waves, conflict, n_waves = waves_from_coloring(routes)
    print(f"\n{n_waves} evacuation waves (graph coloring of the conflict graph):")
    for w in sorted(waves):
        print(f"  Wave {w}: {waves[w]}")

    # =====================================================================
    header("7. DISCRETE-TIME SIMULATION  (Unit 4: recurrence, live re-plan)")
    # =====================================================================
    sim_graph2 = rebuild_graph(sc)
    log_entries = []
    result = run_simulation(sim_graph2, POPULATION, ALLOWED_EXITS, list(EVENTS),
                             log=lambda t, s: log_entries.append((t, s)))
    for t, msg in log_entries:
        print(f"  [t={t:02d}] {msg}")
    print(f"\nCompletion tick per room: {result['completion_tick']}")
    print(f"\nSIMULATED total evacuation time: {result['total_time']} minutes")
    if math.isfinite(tight_bound):
        gap = result["total_time"] - tight_bound
        print(f"Provable floor was {tight_bound} min -> {gap} min above the theoretical minimum "
              f"({100*gap/tight_bound:.1f}% overhead from real routing/collision constraints)")

    # =====================================================================
    header("8. COMPLEXITY COMPARISON  (brute force vs greedy vs optimized)")
    # =====================================================================
    if total_configs <= 200_000:
        bf = brute_force(ALLOWED_EXITS, POPULATION, EXIT_CAPACITY)
        print(f"Brute force: {bf['cost']} min (searched {bf['configurations_tried']} "
              f"configs in {bf['seconds']*1000:.2f} ms)")
    else:
        print(f"Brute force skipped -- {total_configs} configurations is already too many "
              f"to enumerate (this IS the point of Section 7's growth table).")
    gd = greedy_nearest_exit(routes, POPULATION, EXIT_CAPACITY)
    print(f"Greedy (nearest exit, no coordination): {gd['cost']} min (ignores collisions)")
    print(f"Optimized (flow+matching+coloring, this system): {result['total_time']} min "
          f"(the only figure that is actually achievable)")

    print("\nSearch-space growth, brute force vs. one polynomial pass:")
    rows = growth_experiment()
    print(f"{'rooms':<8}{'search space':<16}{'brute force (s)':<18}{'optimized (s)':<16}")
    for row in rows:
        print(f"{row['rooms']:<8}{row['search_space']:<16}"
              f"{row['brute_force_seconds']:<18.6f}{row['optimized_seconds']:<16.8f}")

    # =====================================================================
    header("SUMMARY")
    # =====================================================================
    print(f"{total_people} people, {len(EXITS)} exit(s), {len(EVENTS)} live event(s) scheduled.")
    if math.isfinite(tight_bound):
        print(f"Provable floor: {tight_bound} min   |   Achieved: {result['total_time']} min")
    if MARSHALS:
        print(f"Manual marshal coverage: {len(match_right)}/{len(ROOMS)} rooms only.")
    if stranded:
        print(f"WARNING: {stranded} have NO route to any allowed exit under current "
              f"constraints -- they never leave in this simulation (see Section 5).")

    # =====================================================================
    # Optional: live colourised replay + PNG export
    # =====================================================================
    if yes("\nPlay the colourised live simulation in this terminal now?"):
        animate.play(result["history"], POPULATION, log_entries, delay=0.5)

    if yes("Export a PNG diagram (graph coloured by wave + occupancy chart)?"):
        path = visualize.export(sim_graph, POPULATION, waves, result["history"], EXITS)
        if path:
            print(f"Saved: {path}")


if __name__ == "__main__":
    main()
