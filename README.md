# EVACUATELAB — Dynamic Emergency Evacuation Optimizer

A four-person DSA + Discrete Mathematics course project that models a building as a weighted, capacitated graph, compares routing policies, simulates evacuation waves, and replans when corridors become unavailable.

> **Safety disclaimer:** This is an academic simulation only. It is not certified life-safety software and must not be used to direct a real evacuation. Real buildings require fire-code compliance, qualified safety engineering, accessibility planning, validated crowd models, and on-site emergency procedures.

## Run the interactive UI

**Option A — easiest:** open `index.html` directly in a modern browser.

**Option B — local web server:**

```bash
python serve.py
```

Then open `http://127.0.0.1:8000`. The server uses Python's standard library; no package installation is required. The UI is client-side and does not upload your scenario. Google Fonts are an optional external visual enhancement; system fallbacks are provided.

## What is included

- **Command center:** responsive dark dashboard, interactive graph editor, draggable rooms/exits, corridor creation, node/corridor inspector, capacities, walking time and blockages.
- **Animated simulation:** moving groups, occupant counts, elapsed model ticks, progress, pause/resume, speed control and rerouting after a corridor is blocked.
- **Routing policies:** fastest (Dijkstra by walking time), balanced (walking time with a capacity penalty), and capacity-first (walking time penalized for low-capacity edges). These are heuristics, not globally optimal evacuation schedules.
- **Network analysis:** room reachability, a simplified max-flow throughput estimate, shared-route conflict graph, greedy graph coloring into sequential waves, and heuristic bottleneck indicator.
- **Algorithm lab:** compares the three routing policies against the same graph, displays measured planner runtime and estimated model duration, and exports benchmark CSV.
- **Scenario library:** sample campus, high-density test, randomized building, save/load scenarios for the current session, JSON scenario export and JSON drag-and-drop import.
- **Event log:** simulation start, corridor failures, rerouting, and completion events.
- **Python algorithm modules:** independently runnable Dijkstra, Edmonds–Karp max-flow, bipartite matching, greedy graph coloring, combinatorics, simulation, complexity experiment and optional PNG reporting from the original project.
- **Regression tests:** `python -m unittest -v`.

## Python console analysis (original analytical pipeline)

```bash
python main.py
```

The console application lets you choose the reference campus, define a building interactively, or generate a random building. Optional PNG export uses `matplotlib`; console colour support uses `colorama`.

Optional packages:

```bash
pip install matplotlib colorama networkx
```

## UI controls

- **Select:** click an element to inspect it; drag a node to reposition it.
- **Room / Exit:** choose the tool, then click an empty part of the map.
- **Corridor:** click two nodes in sequence.
- **Toggle blockage:** click a corridor to block/reopen it. During a running simulation, the route plan is recomputed.
- **Inspector:** update room population, exit throughput, corridor walk time/capacity, or blockage.
- **Run / Pause:** start or pause a model. Use automatic incident injection to demonstrate failure handling.
- **Algorithm lab:** run the benchmark and download CSV.
- **Export scenario:** download the graph as JSON. To import, drag a compatible JSON file onto the map area.

## How the model works

1. The building is a graph `G=(V,E)`. Nodes represent rooms/exits; corridors carry a walking-time weight, a per-tick capacity, and a blocked flag.
2. Dijkstra selects a route from each occupied room to the nearest reachable exit under the selected edge-cost policy.
3. A conflict graph links rooms whose planned routes share a corridor. A greedy Welsh–Powell-style coloring assigns conflict-free *planning waves*.
4. The simplified simulation releases people in waves according to the minimum corridor capacity on each route. Moving groups are animated along the route. A route failure triggers replanning for the next tick.
5. The algorithm lab measures route-planner wall-clock time using `performance.now()` and estimates model duration from route length, capacity and wave ordering. Runtime is machine-dependent. Estimated duration is not a proof of optimality.
6. The reachability check and max-flow estimate are separate diagnostics. The simple max-flow network does not model time-expanded crowd movement; its result should not be interpreted as a certified real-world evacuation throughput.

## Known modelling limitations (be transparent in your report)

- This is a deterministic teaching model. It does not simulate smoke/fire propagation, individual walking speeds, mobility needs, panic, counterflow, visibility, dynamic queue formation, or validated corridor-density relationships.
- The routing strategies are heuristics. The benchmark is an experiment on the current input, not evidence that one method is always superior.
- Greedy coloring is a heuristic; it creates non-conflicting planning waves for the modeled shared-corridor constraint but does not by itself prove collision-free physical movement.
- The model's time and capacity units are illustrative. Do not call them calibrated predictions.
- The JavaScript UI and Python CLI are two educational implementations of related algorithms, not a distributed real-time control system.

## Four-person work split

1. **Graph algorithms:** graph representation, BFS/DFS/reachability, Dijkstra, blocked-edge handling and tests.
2. **Optimization & mathematics:** conflict graph, greedy coloring, flow/matching, lower-bound discussion and model assumptions.
3. **UI & integration:** responsive dashboard, graph editor, inspector, animations, import/export and interaction testing.
4. **Simulation & experiments:** scenario generation, dynamic incident cases, repeatable benchmark workloads, CSV analysis and report charts.

Everyone should review the overall model and understand its limitations before the viva.

## Test the Python modules

```bash
python -m unittest -v
python -m py_compile *.py
```

## Suggested report title

**EvacuateLab: An Interactive Graph-Based Emergency Evacuation Simulation and Algorithm Comparison Platform**
