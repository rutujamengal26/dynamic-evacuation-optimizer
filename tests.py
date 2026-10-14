"""Small regression checks for the Python graph algorithms in this project.
Run with: python -m unittest -v
"""
import unittest
from graph import Graph
from algorithms import dijkstra, reconstruct_path, edmonds_karp, bipartite_matching, greedy_coloring

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

if __name__ == "__main__":
    unittest.main()
