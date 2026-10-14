"""
graph.py
--------
Minimal weighted + capacitated graph used to model the building.

Every corridor has TWO independent numbers, because they answer two
different mathematical questions:

    weight   (minutes)     -> "how long does it take to walk it?"   (Unit 6: shortest path)
    capacity (people/min)  -> "how many people can flow through it?" (Unit 6: max-flow)

An edge can be BLOCKED at any time (fire, debris, a jam) without being
removed from the graph -- this is what lets the simulator re-plan live.
"""

from collections import defaultdict


class Graph:
    def __init__(self):
        self.adj = defaultdict(dict)   # adj[u][v] = {'weight', 'capacity', 'blocked'}
        self.nodes = set()

    def add_edge(self, u, v, weight=1, capacity=10**9):
        self.nodes.update([u, v])
        self.adj[u][v] = {"weight": weight, "capacity": capacity, "blocked": False}
        self.adj[v][u] = {"weight": weight, "capacity": capacity, "blocked": False}

    def block(self, u, v):
        if v in self.adj[u]:
            self.adj[u][v]["blocked"] = True
            self.adj[v][u]["blocked"] = True

    def unblock(self, u, v):
        if v in self.adj[u]:
            self.adj[u][v]["blocked"] = False
            self.adj[v][u]["blocked"] = False

    def is_open(self, u, v):
        return v in self.adj[u] and not self.adj[u][v]["blocked"]

    def open_neighbors(self, u):
        """(neighbor, edge_data) pairs for edges that are currently usable."""
        return [(v, d) for v, d in self.adj[u].items() if not d["blocked"]]

    def edges(self):
        seen = set()
        for u in self.adj:
            for v, d in self.adj[u].items():
                if (v, u) not in seen:
                    seen.add((u, v))
                    yield u, v, d

    def degree(self, u):
        """Unit 6: degree of a vertex (only counting open edges)."""
        return len(self.open_neighbors(u))

    def is_connected(self, source, targets):
        """BFS reachability check -- used before planning to catch cut-off rooms."""
        seen = {source}
        stack = [source]
        while stack:
            u = stack.pop()
            for v, d in self.open_neighbors(u):
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        return {t: (t in seen) for t in targets}
