"""
building.py
-----------
The sample campus:

                 BLOCKED
                    X
                    |
        A ---- B ---C ---- D
        |           |      |
       E            F      G
        |           |      |
       H -----------I ---- EXIT1
                    |
                  EXIT2

Corridor C-D is blocked from the start. EXIT1 handles 30 people/min,
EXIT2 handles 20 people/min. Room H is restricted to EXIT2 only
(a routing rule, not a physical limit -- e.g. a safety policy).
"""

from graph import Graph

ROOMS = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]
EXITS = ["EXIT1", "EXIT2"]

# 200 people distributed across the 9 rooms
POPULATION = {
    "A": 25, "B": 20, "C": 30, "D": 15, "E": 20,
    "F": 25, "G": 15, "H": 20, "I": 30,
}
assert sum(POPULATION.values()) == 200

EXIT_CAPACITY = {"EXIT1": 30, "EXIT2": 20}  # people / minute

# room -> exits it is ALLOWED to use (a policy/structural constraint,
# independent of whether it is physically reachable)
ALLOWED_EXITS = {
    "A": ["EXIT1", "EXIT2"], "B": ["EXIT1", "EXIT2"], "C": ["EXIT1", "EXIT2"],
    "D": ["EXIT1"],           "E": ["EXIT1", "EXIT2"], "F": ["EXIT1", "EXIT2"],
    "G": ["EXIT1"],           "H": ["EXIT2"],           "I": ["EXIT1", "EXIT2"],
}

# a handful of staff who can each only shepherd a nearby cluster of rooms
MARSHALS = {
    "M1": ["A", "B", "E"],
    "M2": ["B", "C", "F"],
    "M3": ["D", "G"],
    "M4": ["H", "I"],
}


def build_campus():
    g = Graph()
    # (u, v, walking-time minutes, corridor capacity people/min)
    corridors = [
        ("A", "B", 1, 25),
        ("B", "C", 1, 20),
        ("C", "D", 1, 20),   # blocked below
        ("A", "E", 1, 18),
        ("C", "F", 1, 15),
        ("D", "G", 1, 15),
        ("E", "H", 2, 18),
        ("F", "I", 1, 22),
        ("G", "EXIT1", 1, 30),
        ("H", "I", 1, 20),
        ("I", "EXIT1", 1, 30),
        ("I", "EXIT2", 1, 20),
    ]
    for u, v, w, c in corridors:
        g.add_edge(u, v, weight=w, capacity=c)
    g.block("C", "D")
    return g


def scheduled_events():
    """
    (tick, action) -- injected mid-simulation to prove the system replans
    live, mid-wave, for a room that is actively in the middle of moving
    (not one that already finished or hasn't started yet).
    """
    return [
        (9, ("block", "F", "I")),   # fires exactly as room F starts evacuating
    ]
