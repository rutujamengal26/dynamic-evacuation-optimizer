"""
algorithms.py
-------------
Four classical discrete-math algorithms, each solving a genuinely
different sub-problem of the evacuation plan:

    dijkstra()          Unit 6 -- fastest route from a room to a target
    edmonds_karp()       Unit 6 -- true max sustainable evacuation RATE
                          (also returns the min-cut: the real bottleneck)
    bipartite_matching() Unit 6 -- Kuhn's algorithm + Hall's theorem check
    greedy_coloring()     Unit 6 -- turns a conflict graph into evacuation "waves"
"""

import heapq
import math
from collections import deque, defaultdict


# ----------------------------------------------------------------------
# 1. DIJKSTRA -- fastest route (by walking time) from a room to a target
# ----------------------------------------------------------------------
def dijkstra(graph, source):
    dist = {n: math.inf for n in graph.nodes}
    prev = {}
    dist[source] = 0
    pq = [(0, source)]
    visited = set()
    while pq:
        d, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)
        for v, data in graph.open_neighbors(u):
            nd = d + data["weight"]
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    return dist, prev


def reconstruct_path(prev, source, target):
    if target == source:
        return [source]
    if target not in prev:
        return None
    path = [target]
    while path[-1] != source:
        path.append(prev[path[-1]])
    return list(reversed(path))


# ----------------------------------------------------------------------
# 2. EDMONDS-KARP -- max-flow (Ford-Fulkerson with BFS augmenting paths)
#    Gives the true max people/min the WHOLE network can sustain, and,
#    via the min-cut, exactly which edges are the bottleneck.
# ----------------------------------------------------------------------
def edmonds_karp(graph, source, sink):
    # Every corridor is undirected, so it can carry up to its full capacity
    # in EITHER direction (just not represented as a signed net flow here --
    # a standard, explainable simplification for an undirected capacity graph).
    residual = defaultdict(dict)
    for u, v, d in graph.edges():
        if d["blocked"]:
            continue
        residual[u][v] = residual[u].get(v, 0) + d["capacity"]
        residual[v][u] = residual[v].get(u, 0) + d["capacity"]

    def bfs_path():
        parent = {source: None}
        q = deque([source])
        while q:
            u = q.popleft()
            for v, cap in residual[u].items():
                if cap > 0 and v not in parent:
                    parent[v] = u
                    if v == sink:
                        return parent
                    q.append(v)
        return None

    max_flow = 0
    trace = []  # list of (path, bottleneck) -- this IS a flow decomposition,
                # i.e. a concrete set of routes + rates we can hand to the simulator
    while True:
        parent = bfs_path()
        if parent is None:
            break
        path, v = [], sink
        while v is not None:
            path.append(v)
            v = parent[v]
        path.reverse()
        bottleneck = min(residual[path[i]][path[i + 1]] for i in range(len(path) - 1))
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            residual[u][v] -= bottleneck
            residual[v][u] += bottleneck
        max_flow += bottleneck
        trace.append((path, bottleneck))

    # Min cut: nodes reachable from source in the FINAL residual graph
    reachable = {source}
    q = deque([source])
    while q:
        u = q.popleft()
        for v, cap in residual[u].items():
            if cap > 0 and v not in reachable:
                reachable.add(v)
                q.append(v)
    cut_edges = [(u, v) for u, v, d in graph.edges()
                 if not d["blocked"] and u in reachable and v not in reachable]

    return max_flow, trace, cut_edges


# ----------------------------------------------------------------------
# 3. BIPARTITE MATCHING -- Kuhn's algorithm (augmenting paths)
#    Used for: "can every room be covered by a marshal?"
#    Also reports a Hall-theorem deficiency witness when it can't.
# ----------------------------------------------------------------------
def bipartite_matching(left_nodes, right_neighbors):
    """
    left_nodes        : iterable of left-side ids
    right_neighbors    : dict left_id -> list of right_id it can connect to
    returns (match_right -> left, unmatched_left_list)
    """
    match_right = {}   # right_id -> left_id

    def try_augment(u, visited):
        for v in right_neighbors.get(u, []):
            if v in visited:
                continue
            visited.add(v)
            if v not in match_right or try_augment(match_right[v], visited):
                match_right[v] = u
                return True
        return False

    unmatched = []
    for u in left_nodes:
        if not try_augment(u, set()):
            unmatched.append(u)
    return match_right, unmatched


def hall_deficiency(subset, right_neighbors):
    """Neighborhood N(S) of a subset S of the left side -- for demonstrating Hall's theorem."""
    neighborhood = set()
    for u in subset:
        neighborhood.update(right_neighbors.get(u, []))
    return neighborhood


# ----------------------------------------------------------------------
# 4. GREEDY (WELSH-POWELL STYLE) GRAPH COLORING -- conflict graph -> waves
#    Color i = "evacuation wave i". Two rooms get different colors iff
#    their planned routes would collide on a shared corridor.
# ----------------------------------------------------------------------
def greedy_coloring(conflict_adj):
    """conflict_adj: dict node -> set of conflicting nodes."""
    order = sorted(conflict_adj, key=lambda n: -len(conflict_adj[n]))  # Welsh-Powell order
    color = {}
    for node in order:
        used = {color[nb] for nb in conflict_adj[node] if nb in color}
        c = 0
        while c in used:
            c += 1
        color[node] = c
    return color  # node -> wave number (0-indexed)
