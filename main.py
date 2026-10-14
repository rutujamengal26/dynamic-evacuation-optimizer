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
from algorithms import edmonds_karp, bipartite_matching, hall_deficiency
from combinatorics import count_configurations, pigeonhole_time_bound, maxflow_time_bound, inclusion_exclusion_exit_access
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

    # =====================================================================
    header("2. COMBINATORICS  (Unit 2 & 3: counting, pigeonhole)")
    # =====================================================================
    total_configs, per_room = count_configurations(ALLOWED_EXITS)
    print(f"Per-room exit choices: {per_room}")
    print(f"Multiplication principle -> {' x '.join(str(v) for v in per_room.values())} "
          f"= {total_configs} configurations")

    naive_bound, total_cap = pigeonhole_time_bound(total_people, EXIT_CAPACITY)
    print(f"\nPigeonhole bound: {total_people} people, {total_cap}/min combined exit capacity.")
    print(f"No schedule can beat ceil({total_people}/{total_cap}) = {naive_bound} minutes.")

    if len(EXITS) == 2:
        ie = inclusion_exclusion_exit_access(ALLOWED_EXITS, EXITS)
        u, chk = ie["union_check"]
        print(f"\nInclusion-Exclusion on exit access: |union|={u} via direct count, "
              f"{chk} via |A|+|B|-|A^B| -> match")

    # =====================================================================
    header("3. MAX-FLOW  (Unit 6: Edmonds-Karp, min-cut)")
    # =====================================================================
    flow_g = rebuild_graph(sc)
    flow_g.add_edge("SOURCE", ROOMS[0], weight=0, capacity=10**9)
    for r in ROOMS[1:]:
        flow_g.add_edge("SOURCE", r, weight=0, capacity=10**9)
    for e in EXITS:
        flow_g.add_edge(e, "SINK", weight=0, capacity=EXIT_CAPACITY[e])

    max_flow, trace, cut_edges = edmonds_karp(flow_g, "SOURCE", "SINK")
    print(f"Max sustainable evacuation rate: {max_flow} people/min")
    for path, bn in trace:
        print(f"  {' -> '.join(path):45s} +{bn}/min")
    print(f"Min-cut (true bottleneck): {cut_edges}")

    tight_bound = maxflow_time_bound(total_people, max_flow) if max_flow > 0 else float("inf")
    print(f"\nMax-flow-based lower bound: {tight_bound} minutes "
          f"(>= naive pigeonhole {naive_bound})")

    # =====================================================================
    header("4. BIPARTITE MATCHING  (Unit 6: Kuhn's algorithm, Hall's theorem)")
    # =====================================================================
    match_right = {}
    if MARSHALS:
        match_right, unmatched = bipartite_matching(list(MARSHALS), MARSHALS)
        for room, marshal in match_right.items():
            print(f"  {marshal} covers {room}")
        covered = set(match_right.keys())
        uncovered = [r for r in ROOMS if r not in covered]
        print(f"\nMax matching: {len(match_right)}/{len(ROOMS)} rooms covered. Uncovered: {uncovered}")
        if uncovered:
            witness = set(uncovered[:2]) if len(uncovered) >= 2 else set(uncovered)
            nbhd = hall_deficiency(witness, MARSHALS)
            print(f"Hall's theorem witness: N({sorted(witness)}) = {sorted(nbhd)} "
                  f"-> |N(S)|={len(nbhd)} < |S|={len(witness)}  FAILS -> automation required")
    else:
        print("(no marshal roster defined for this scenario -- skipping)")

    # =====================================================================
    header("5. ROUTE PLANNING + GRAPH COLORING  (Unit 6: Dijkstra, coloring)")
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
    header("6. DISCRETE-TIME SIMULATION  (Unit 4: recurrence, live re-plan)")
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
    header("7. COMPLEXITY COMPARISON  (brute force vs greedy vs optimized)")
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
