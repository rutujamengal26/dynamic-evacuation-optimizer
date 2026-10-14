"""
scenario.py
-----------
Where the "is this hardcoded?" question gets answered: this module builds
the graph + population + constraints + live events EITHER from
  (a) the sample campus used in the project report,
  (b) numbers the user types in at the terminal, or
  (c) a randomly generated building (different every run unless seeded),
and hands all three back in the exact same shape so the rest of the
pipeline (algorithms.py, combinatorics.py, simulation.py) never needs to
know or care which one was used.
"""

import random
from graph import Graph
import building as default_building


def _prompt(msg, default=None):
    raw = input(f"{msg}" + (f" [{default}]: " if default is not None else ": ")).strip()
    return raw if raw else default


def load_default():
    g = default_building.build_campus()
    return {
        "graph": g,
        "rooms": list(default_building.ROOMS),
        "exits": list(default_building.EXITS),
        "population": dict(default_building.POPULATION),
        "exit_capacity": dict(default_building.EXIT_CAPACITY),
        "allowed_exits": {k: list(v) for k, v in default_building.ALLOWED_EXITS.items()},
        "marshals": {k: list(v) for k, v in default_building.MARSHALS.items()},
        "events": default_building.scheduled_events(),
        "label": "sample campus from the project report",
    }


def load_random(n_rooms=None, seed=None):
    rnd = random.Random(seed)
    n_rooms = n_rooms or rnd.randint(6, 12)
    rooms = [chr(ord("A") + i) for i in range(n_rooms)]
    exits = ["EXIT1", "EXIT2"] if n_rooms < 10 else ["EXIT1", "EXIT2", "EXIT3"]

    g = Graph()
    # random spanning tree guarantees every room is connected to something
    connected = [rooms[0]]
    for r in rooms[1:]:
        u = rnd.choice(connected)
        g.add_edge(u, r, weight=rnd.randint(1, 3), capacity=rnd.randint(12, 28))
        connected.append(r)
    # a few extra edges so the graph isn't just a bare tree
    for _ in range(max(1, n_rooms // 3)):
        u, v = rnd.sample(rooms, 2)
        if v not in g.adj[u]:
            g.add_edge(u, v, weight=rnd.randint(1, 3), capacity=rnd.randint(12, 28))
    # attach each exit to one or two random rooms
    exit_capacity = {}
    for e in exits:
        exit_capacity[e] = rnd.randint(15, 35)
        for _ in range(rnd.randint(1, 2)):
            room = rnd.choice(rooms)
            g.add_edge(room, e, weight=1, capacity=rnd.randint(15, 30))

    population = {r: rnd.randint(10, 40) for r in rooms}
    allowed_exits = {}
    for r in rooms:
        if rnd.random() < 0.25:
            allowed_exits[r] = [rnd.choice(exits)]          # ~25% of rooms restricted
        else:
            allowed_exits[r] = list(exits)

    # block one random corridor from the start
    all_room_edges = [(u, v) for u, v, d in g.edges() if u in rooms and v in rooms]
    if all_room_edges:
        bu, bv = rnd.choice(all_room_edges)
        g.block(bu, bv)

    events = []
    if len(all_room_edges) > 1:
        eu, ev = rnd.choice(all_room_edges)
        events.append((rnd.randint(3, 8), ("block", eu, ev)))

    marshals = {}
    n_marshals = max(2, n_rooms // 2)
    for i in range(n_marshals):
        marshals[f"M{i+1}"] = rnd.sample(rooms, k=min(3, n_rooms))

    return {
        "graph": g, "rooms": rooms, "exits": exits, "population": population,
        "exit_capacity": exit_capacity, "allowed_exits": allowed_exits,
        "marshals": marshals, "events": events,
        "label": f"randomly generated building (seed={seed}, {n_rooms} rooms)",
    }


def load_from_terminal():
    print("\nEnter rooms as a comma-separated list, e.g.  A,B,C,D")
    rooms = [r.strip() for r in _prompt("Rooms").split(",") if r.strip()]

    print("\nEnter exits as `NAME CAPACITY`, one per line (blank line to stop),")
    print("e.g.  EXIT1 30")
    exit_capacity = {}
    while True:
        line = input("Exit: ").strip()
        if not line:
            break
        name, cap = line.split()
        exit_capacity[name] = int(cap)
    exits = list(exit_capacity)

    print("\nEnter corridors as `U V WEIGHT CAPACITY` (U,V can be rooms or exits),")
    print("one per line, blank line to stop. e.g.  A B 1 20")
    g = Graph()
    while True:
        line = input("Corridor: ").strip()
        if not line:
            break
        u, v, w, c = line.split()
        g.add_edge(u, v, weight=int(w), capacity=int(c))

    print("\nEnter population as `ROOM COUNT`, blank line to stop.")
    population = {r: 0 for r in rooms}
    while True:
        line = input("Population: ").strip()
        if not line:
            break
        r, n = line.split()
        population[r] = int(n)

    print("\nRestrict a room to specific exits? `ROOM EXIT1,EXIT2` (blank to stop,")
    print("unlisted rooms default to ALL exits allowed).")
    allowed_exits = {r: list(exits) for r in rooms}
    while True:
        line = input("Restriction: ").strip()
        if not line:
            break
        r, ex = line.split()
        allowed_exits[r] = ex.split(",")

    print("\nBlock any corridors from the start? `U V` (blank line to stop)")
    while True:
        line = input("Block: ").strip()
        if not line:
            break
        u, v = line.split()
        g.block(u, v)

    print("\nSchedule ONE live failure mid-simulation? `TICK U V` (blank = none)")
    events = []
    line = input("Event: ").strip()
    if line:
        t, u, v = line.split()
        events.append((int(t), ("block", u, v)))

    return {
        "graph": g, "rooms": rooms, "exits": exits, "population": population,
        "exit_capacity": exit_capacity, "allowed_exits": allowed_exits,
        "marshals": {}, "events": events, "label": "custom building entered at the terminal",
    }


def choose_scenario():
    print("=" * 72)
    print("Choose a scenario:")
    print("  1) Sample campus from the project report (fast, matches the report)")
    print("  2) Enter a custom building at the terminal (fully dynamic)")
    print("  3) Generate a random building (different every run)")
    choice = _prompt("Choice", default="1")
    if choice == "2":
        return load_from_terminal()
    if choice == "3":
        seed = _prompt("Random seed (blank = different every time)", default="")
        seed = int(seed) if seed else None
        n = _prompt("Number of rooms (blank = random 6-12)", default="")
        n = int(n) if n else None
        return load_random(n_rooms=n, seed=seed)
    return load_default()
