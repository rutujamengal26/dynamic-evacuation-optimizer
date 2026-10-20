"""Small regression checks for the Python graph algorithms in this project.
Run with: python -m unittest -v
"""
import unittest
from graph import Graph
from algorithms import (
    dijkstra, reconstruct_path, edmonds_karp, bipartite_matching,
    greedy_coloring, hall_deficiency_witness, edge_disjoint_connectivity,
)
from advanced_networks import min_cost_exit_assignment, time_expanded_evacuation_bound
from combinatorics import generalized_pigeonhole_bound, inclusion_exclusion_union_count
from simulation import plan_routes, waves_from_coloring, run_simulation

class AlgorithmTests(unittest.TestCase):
    def setUp(self):
        self.g = Graph()
        self.g.add_edge("A", "B", weight=2, capacity=5)
        self.g.add_edge("B", "EXIT", weight=2, capacity=4)
        self.g.add_edge("A", "C", weight=1, capacity=2)
        self.g.add_edge("C", "EXIT", weight=8, capacity=2)

    def test_dijkstra_chooses_fastest_path(self):
        dist, prev = dijkstra(self.g, "A")
        self.assertEqual(dist["EXIT"], 4)
        self.assertEqual(reconstruct_path(prev, "A", "EXIT"), ["A", "B", "EXIT"])

    def test_blocked_corridor_is_not_used(self):
        self.g.block("B", "EXIT")
        dist, prev = dijkstra(self.g, "A")
        self.assertEqual(dist["EXIT"], 9)
        self.assertEqual(reconstruct_path(prev, "A", "EXIT"), ["A", "C", "EXIT"])

    def test_max_flow_respects_exit_capacity(self):
        flow, trace, cut = edmonds_karp(self.g, "A", "EXIT")
        self.assertEqual(flow, 6)
        self.assertTrue(trace)

    def test_matching_assigns_distinct_right_vertices(self):
        matching, unmatched = bipartite_matching(["room1", "room2"], {"room1": ["m1", "m2"], "room2": ["m1"]})
        self.assertEqual(len(matching), 2)
        self.assertEqual(unmatched, [])

    def test_greedy_coloring_separates_conflicts(self):
        coloring = greedy_coloring({"A": {"B"}, "B": {"A", "C"}, "C": {"B"}})
        self.assertNotEqual(coloring["A"], coloring["B"])
        self.assertNotEqual(coloring["B"], coloring["C"])

    def test_hall_witness_uses_matching_left_side(self):
        neighbors = {"m1": ["r1"], "m2": ["r1"]}
        matching, _ = bipartite_matching(["m1", "m2"], neighbors)
        subset, neighborhood = hall_deficiency_witness(
            ["m1", "m2"], neighbors, matching)
        self.assertEqual(subset, {"m1", "m2"})
        self.assertEqual(neighborhood, {"r1"})
        self.assertLess(len(neighborhood), len(subset))

    def test_edge_disjoint_routes_and_minimum_cut(self):
        graph = Graph()
        graph.add_edge("A", "B", capacity=10)
        graph.add_edge("B", "X", capacity=10)
        graph.add_edge("A", "C", capacity=10)
        graph.add_edge("C", "X", capacity=10)
        count, cut = edge_disjoint_connectivity(graph, "A", "X")
        self.assertEqual(count, 2)
        self.assertEqual(len(cut), 2)

    def test_time_expanded_flow_respects_per_tick_corridor_capacity(self):
        graph = Graph()
        graph.add_edge("A", "EXIT", weight=1, capacity=1)
        result = time_expanded_evacuation_bound(
            graph, {"A": 3}, ["EXIT"], {"EXIT": 2})
        self.assertEqual(result["minimum_ticks"], 3)
        self.assertTrue(result["complete"])

    def test_min_cost_exit_assignment_respects_allowed_exits(self):
        graph = Graph()
        graph.add_edge("A", "EXIT1", weight=2, capacity=1)
        graph.add_edge("A", "EXIT2", weight=1, capacity=1)
        result = min_cost_exit_assignment(
            graph, {"A": 2}, {"A": ["EXIT1", "EXIT2"]},
            ["EXIT1", "EXIT2"], {"EXIT1": 1, "EXIT2": 1}, horizon=1)
        self.assertEqual(result["evacuated"], 2)
        self.assertEqual(result["total_cost"], 3)
        self.assertEqual(result["assignments"]["A"], {"EXIT1": 1, "EXIT2": 1})

    def test_generalized_pigeonhole_and_inclusion_exclusion(self):
        self.assertEqual(generalized_pigeonhole_bound(10, 3), 4)
        count, _ = inclusion_exclusion_union_count([
            {"a", "b"}, {"b", "c"}, {"b"},
        ])
        self.assertEqual(count, 3)

    def test_route_and_wave_invariants(self):
        routes, stranded = plan_routes(self.g, ["A"], {"A": ["EXIT"]})
        self.assertEqual(stranded, [])
        self.assertEqual(routes["A"]["path"][0], "A")
        self.assertIn(routes["A"]["path"][-1], {"EXIT"})
        for u, v in zip(routes["A"]["path"], routes["A"]["path"][1:]):
            self.assertTrue(self.g.is_open(u, v))

        waves, conflicts, _ = waves_from_coloring(routes)
        wave_by_room = {
            room: wave for wave, members in waves.items() for room in members
        }
        for room, neighbors in conflicts.items():
            for neighbor in neighbors:
                self.assertNotEqual(wave_by_room[room], wave_by_room[neighbor])

    def test_route_planner_handles_room_already_at_exit(self):
        graph = Graph()
        graph.add_edge("ROOM", "EXIT", weight=2, capacity=3)
        routes, stranded = plan_routes(graph, ["EXIT"], {"EXIT": ["EXIT"]})
        self.assertEqual(stranded, [])
        self.assertEqual(routes["EXIT"]["path"], ["EXIT"])
        self.assertEqual(routes["EXIT"]["bottleneck"], float("inf"))

    def test_simulation_accounts_for_walking_time_and_conserves_population(self):
        result = run_simulation(
            self.g, {"A": 1}, {"A": ["EXIT"]}, [])
        self.assertEqual(result["completion_tick"]["A"], 4)
        self.assertTrue(result["population_conserved"])
        self.assertEqual(result["evacuated_people"], 1)

    def test_simulation_eventually_clears_reachable_population(self):
        result = run_simulation(
            self.g, {"A": 10}, {"A": ["EXIT"]}, [])
        self.assertEqual(result["history"][-1][2]["A"], 0)
        self.assertEqual(result["completion_tick"]["A"], result["total_time"])

if __name__ == "__main__":
    unittest.main()
