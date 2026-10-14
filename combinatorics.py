"""
combinatorics.py
-----------------
Three pieces of "pure counting" that earn their place because each
answers a question the graph algorithms alone cannot:

    count_configurations()   Unit 2  -- how big is the brute-force search space?
    pigeonhole_time_bound()  Unit 3  -- a PROVABLE minimum evacuation time,
                                         true no matter how clever the routing is
    inclusion_exclusion_exit_access()  Unit 3 -- how many rooms are "flexible"
                                         (reach both exits) vs "fixed" (only one)
"""

import math
from functools import reduce


def count_configurations(allowed_exits):
    """
    Generalized counting: the number of ways to assign every room to ONE
    of its allowed exits is the product of the per-room choice counts
    (multiplication principle). This is exactly the space brute force
    would have to search.
    """
    per_room_choices = {room: len(exits) for room, exits in allowed_exits.items()}
    total = reduce(lambda a, b: a * b, per_room_choices.values(), 1)
    return total, per_room_choices


def pigeonhole_time_bound(total_people, exit_capacities):
    """
    Naive pigeonhole bound: if EVERY exit ran at its own maximum capacity
    with zero interference, the fastest the building could possibly empty
    is population / (sum of exit capacities). No schedule can beat this --
    if it claims to, more people would have to leave per minute than the
    exits can physically pass, a direct pigeonhole contradiction.
    """
    total_capacity = sum(exit_capacities.values())
    return math.ceil(total_people / total_capacity), total_capacity


def maxflow_time_bound(total_people, max_flow_rate):
    """
    Tighter bound using the network's true max-flow rate (which already
    accounts for internal corridor bottlenecks, not just exit doors).
    By max-flow/min-cut, max_flow_rate IS the most people/min that can
    ever cross the min cut -- so this bound can only be >= the naive one.
    """
    return math.ceil(total_people / max_flow_rate)


def inclusion_exclusion_exit_access(allowed_exits, exit_names):
    """
    |A u B| = |A| + |B| - |A n B|  applied to "rooms that can reach exit X".
    Confirms every room is accounted for exactly once and separates
    rooms with real routing flexibility from rooms locked to one exit.
    """
    sets = {e: {r for r, exits in allowed_exits.items() if e in exits} for e in exit_names}
    e1, e2 = exit_names
    union = sets[e1] | sets[e2]
    inter = sets[e1] & sets[e2]
    ie_total = len(sets[e1]) + len(sets[e2]) - len(inter)
    assert ie_total == len(union), "inclusion-exclusion mismatch"
    fixed_to_one = union - inter
    return {
        "only_%s" % e1: sets[e1] - sets[e2],
        "only_%s" % e2: sets[e2] - sets[e1],
        "flexible_both": inter,
        "fixed_to_one": fixed_to_one,
        "union_check": (len(union), ie_total),
    }
