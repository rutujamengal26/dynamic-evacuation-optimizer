"""Additional network-flow models for evacuation analysis.

The time-expanded model is an optimistic throughput bound: all rooms may use
all exits, corridor capacity limits departures per tick, and waiting space is
unlimited. The min-cost assignment respects room-specific exit permissions
and shortest-path travel costs, but models only exit capacity over a horizon.
"""

from collections import defaultdict, deque

from algorithms import dijkstra


def _max_flow(residual, source, sink):
    flow = 0
    while True:
        parent = {source: None}
        queue = deque([source])
        while queue and sink not in parent:
            u = queue.popleft()
            for v, capacity in residual[u].items():
                if capacity > 0 and v not in parent:
                    parent[v] = u
                    queue.append(v)
        if sink not in parent:
            return flow

        amount = float("inf")
        v = sink
        while v != source:
            u = parent[v]
            amount = min(amount, residual[u][v])
            v = u
        v = sink
        while v != source:
            u = parent[v]
            residual[u][v] -= amount
            residual[v][u] = residual[v].get(u, 0) + amount
            v = u
        flow += amount


def _time_expanded_flow(graph, population, exits, exit_capacity, horizon):
    residual = defaultdict(dict)

    def add_edge(u, v, capacity):
        residual[u][v] = residual[u].get(v, 0) + capacity
        residual[v].setdefault(u, 0)

    source, sink = ("source",), ("sink",)
    total_people = sum(population.values())
    for room, people in population.items():
        if people > 0:
            add_edge(source, ("state", room, 0), people)

    for node in graph.nodes:
        for tick in range(horizon):
            add_edge(("state", node, tick), ("state", node, tick + 1), total_people)

    for u, v, data in graph.edges():
        if data["blocked"]:
            continue
        duration = int(data["weight"])
        capacity = int(data["capacity"])
        for tick in range(horizon - duration + 1):
            add_edge(("state", u, tick), ("state", v, tick + duration), capacity)
            add_edge(("state", v, tick), ("state", u, tick + duration), capacity)

    for exit_node in exits:
        capacity = int(exit_capacity[exit_node])
        for tick in range(horizon + 1):
            add_edge(("state", exit_node, tick), sink, capacity)

    return _max_flow(residual, source, sink)


def time_expanded_evacuation_bound(graph, population, exits, exit_capacity,
                                    max_horizon=2048):
    """Find the earliest tick horizon that can carry all occupants in a relaxed model."""
    if max_horizon < 1:
        raise ValueError("max_horizon must be at least 1")
    if any(int(people) != people or people < 0 for people in population.values()):
        raise ValueError("population counts must be non-negative integers")
    if any(int(exit_capacity.get(exit_node, 0)) != exit_capacity.get(exit_node, 0)
           or exit_capacity.get(exit_node, 0) <= 0 for exit_node in exits):
        raise ValueError("every exit must have positive integer capacity")
    for _, _, data in graph.edges():
        weight, capacity = data["weight"], data["capacity"]
        if int(weight) != weight or weight <= 0:
            raise ValueError("time-expanded analysis requires positive integer edge weights")
        if int(capacity) != capacity or capacity <= 0:
            raise ValueError("time-expanded analysis requires positive integer capacities")

    total_people = sum(population.values())
    if total_people == 0:
        return {"minimum_ticks": 0, "evacuated": 0, "total_people": 0,
                "complete": True, "assumptions": "all rooms may use all exits"}

    high = 1
    evacuated = _time_expanded_flow(graph, population, exits, exit_capacity, high)
    while evacuated < total_people and high < max_horizon:
        high = min(high * 2, max_horizon)
        evacuated = _time_expanded_flow(graph, population, exits, exit_capacity, high)
    if evacuated < total_people:
        return {"minimum_ticks": None, "evacuated": evacuated,
                "total_people": total_people, "complete": False,
                "assumptions": "all rooms may use all exits"}

    low = 0
    while low + 1 < high:
        middle = (low + high) // 2
        if _time_expanded_flow(graph, population, exits, exit_capacity, middle) == total_people:
            high = middle
        else:
            low = middle
    return {"minimum_ticks": high, "evacuated": total_people,
            "total_people": total_people, "complete": True,
            "assumptions": "all rooms may use all exits"}


def min_cost_exit_assignment(graph, population, allowed_exits, exits,
                             exit_capacity, horizon):
    """Maximize assigned occupants, then minimize total shortest-path cost."""
    if horizon < 0:
        raise ValueError("horizon must be non-negative")
    if any(int(people) != people or people < 0 for people in population.values()):
        raise ValueError("population counts must be non-negative integers")
    if any(int(exit_capacity.get(exit_node, 0)) != exit_capacity.get(exit_node, 0)
           or exit_capacity.get(exit_node, 0) < 0 for exit_node in exits):
        raise ValueError("exit capacities must be non-negative integers")

    source, sink = ("source",), ("sink",)
    nodes = [source, sink]
    adjacency = defaultdict(list)

    def add_edge(u, v, capacity, cost):
        forward = [v, len(adjacency[v]), capacity, cost]
        reverse = [u, len(adjacency[u]), 0, -cost]
        adjacency[u].append(forward)
        adjacency[v].append(reverse)
        return forward

    for room in population:
        nodes.append(("room", room))
    for exit_node in exits:
        nodes.append(("exit", exit_node))

    route_edges = {}
    for room, people in population.items():
        room_node = ("room", room)
        add_edge(source, room_node, people, 0)
        distances, _ = dijkstra(graph, room)
        for exit_node in allowed_exits.get(room, []):
            if exit_node in exits and distances.get(exit_node, float("inf")) < float("inf"):
                route_edges[(room, exit_node)] = add_edge(
                    room_node, ("exit", exit_node), people, distances[exit_node])

    for exit_node in exits:
        add_edge(("exit", exit_node), sink, exit_capacity[exit_node] * horizon, 0)

    nodes = list(dict.fromkeys(nodes))
    total_flow, total_cost = 0, 0
    while True:
        distance = {node: float("inf") for node in nodes}
        parent = {}
        distance[source] = 0
        for _ in range(len(nodes) - 1):
            changed = False
            for u in nodes:
                if distance[u] == float("inf"):
                    continue
                for index, edge in enumerate(adjacency[u]):
                    v, _, capacity, cost = edge
                    if capacity > 0 and distance[v] > distance[u] + cost:
                        distance[v] = distance[u] + cost
                        parent[v] = (u, index)
                        changed = True
            if not changed:
                break
        if sink not in parent:
            break

        amount = float("inf")
        v = sink
        while v != source:
            u, index = parent[v]
            amount = min(amount, adjacency[u][index][2])
            v = u
        v = sink
        while v != source:
            u, index = parent[v]
            edge = adjacency[u][index]
            edge[2] -= amount
            adjacency[v][edge[1]][2] += amount
            v = u
        total_flow += amount
        total_cost += amount * distance[sink]

    assignments = {room: {} for room in population}
    for (room, exit_node), edge in route_edges.items():
        assigned = edge[2]  # residual capacity starts at the room's population
        assigned = population[room] - assigned
        if assigned:
            assignments[room][exit_node] = assigned
    return {"evacuated": total_flow, "total_cost": total_cost,
            "assignments": assignments, "horizon": horizon,
            "all_evacuated": total_flow == sum(population.values()),
            "assumptions": "room exit permissions and exit capacity respected; corridor capacities omitted"}
