# EvacuateLab — Dynamic Emergency Evacuation Optimizer

EvacuateLab is an interactive, graph-based emergency evacuation simulator that applies **Discrete Mathematics, Graph Theory, and Combinatorial Optimization** to a building evacuation problem.

The project represents a building as a weighted graph, compares evacuation routing strategies, simulates occupant movement in discrete time steps, and recalculates routes when corridors become unavailable. It includes an interactive web interface, an algorithm benchmarking environment, scenario management, and a Python-based analytical pipeline.

> **Safety Disclaimer:** EvacuateLab is an academic simulation, not certified life-safety software. It must not be used to direct real evacuations. Real-world applications require validated models, qualified safety engineering, applicable fire-code compliance, accessibility planning, and established emergency procedures.

## Features

- **Interactive Command Center:** Explore and edit a building network, inspect rooms and exits, configure corridor properties, and manage blocked connections.
- **Evacuation Simulation:** Visualize occupant groups, track model time and evacuation progress, pause or resume simulations, and observe replanning after corridor failures.
- **Routing Strategies:** Compare fastest-route, balanced-cost, and capacity-prioritized routing policies.
- **Graph Analysis:** Examine room reachability, estimate network throughput using a simplified maximum-flow model, construct shared-route conflict graphs, and assign planning waves using greedy graph coloring.
- **Algorithm Lab:** Benchmark routing strategies on the same network, compare measured planner execution times and estimated simulation durations, and export results as CSV.
- **Scenario Library:** Explore sample and randomized networks, save scenarios for the current browser session, and import or export building configurations in JSON format.
- **Event Log:** Review simulation events, corridor failures, route recalculations, and completion status.
- **Python Algorithm Modules:** Explore graph algorithms, maximum flow, bipartite matching, graph coloring, combinatorial calculations, simulation, and complexity experiments.
- **Regression Tests:** Run the Python test suite to check core algorithm behaviour.

## Technology Stack

- **Frontend:** HTML, CSS, and JavaScript
- **Local Server:** Python standard library
- **Algorithms:** Graph traversal, Dijkstra's shortest-path algorithm, Edmonds–Karp maximum flow, bipartite matching, and greedy graph coloring
- **Data Formats:** JSON for scenarios and CSV for benchmark results
- **Optional Visualization and Analysis:** Matplotlib, Colorama, and NetworkX

## Getting Started

### Run the Interactive Web Application

**Option 1: Open Directly**

Open `index.html` in a modern web browser.

**Option 2: Start a Local Server**

Run the following command from the project directory:

```bash
python serve.py
```

Open the application at:

http://127.0.0.1:8000

The local server uses Python's standard library, so no server dependencies need to be installed. The browser interface processes scenarios locally rather than uploading them to a remote application server. Google Fonts may be used as an optional external visual enhancement, with system-font fallbacks available.

### Run the Python Analytical Application

```bash
python main.py
```

The console application supports the available building-definition and scenario-generation workflows.

**Optional dependencies** for additional analytical or visualization features:

```bash
pip install matplotlib colorama networkx
```

Install these packages only if you use the corresponding optional features.

## User Interface Guide

| Control | Function |
|---|---|
| **Select** | Select and inspect a node or connection; reposition nodes when supported. |
| **Room / Exit** | Add a room or exit at a valid location on the map. |
| **Corridor** | Connect two selected nodes. |
| **Block / Reopen** | Change corridor availability and recalculate routes when supported by the active simulation. |
| **Inspector** | Configure room populations, exit throughput, corridor costs, capacities, and blockage status. |
| **Run / Pause** | Start or pause the evacuation simulation. |
| **Algorithm Lab** | Compare routing strategies and export benchmark results. |
| **Scenario Export / Import** | Save a scenario to JSON or load a compatible JSON configuration. |

The exact controls depend on the application version and the active scenario.

## Mathematical Model

### 1. Graph Representation

The building is represented as a graph:

\[
G=(V,E)
\]

where:

- \(V\) is the set of vertices representing rooms, exits, or other modeled locations.
- \(E\) is the set of edges representing permitted connections, such as corridors.
- Each edge can carry a travel-cost weight, capacity, and availability status.

A valid evacuation route must consist of connected, permitted edges leading to an accessible exit.

### 2. Shortest-Path Optimization

Dijkstra's algorithm finds a minimum-cost route when edge costs are non-negative.

For a route \(P\), its total cost is:

\[
C(P)=\sum_{e\in P}w(e)
\]

where \(w(e)\) represents the modeled cost of traversing edge \(e\).

The fastest-route policy prioritizes modeled walking time. The balanced-cost and capacity-prioritized policies adjust route costs using additional penalties. These policies are heuristics and do not guarantee a globally optimal evacuation schedule.

### 3. Reachability Analysis

Graph traversal identifies locations that have a valid path to an available exit. When connections become blocked, reachability must be recalculated to identify locations that are no longer connected to any exit.

### 4. Network Flow

The maximum-flow model estimates the throughput of a capacitated network under its defined constraints. The implementation uses a simplified network representation and does not, by itself, model the full time-dependent movement of a crowd.

### 5. Conflict Graph and Graph Coloring

A conflict graph represents relationships between planned routes that share modeled constrained connections. Greedy graph coloring assigns planning waves so that conflicting routes receive different colors under the encoded conflict rules.

Graph coloring is a heuristic scheduling aid. It does not prove that physical movement will be collision-free or that the resulting schedule minimizes total evacuation time.

### 6. Discrete Simulation and Benchmarking

The simulator advances through discrete model time steps, updating occupant progress and responding to connection failures according to its implemented rules.

The Algorithm Lab measures planner execution time using the browser's `performance.now()` API. Estimated simulation duration is calculated from the model's assumptions and route-planning logic. Execution time is machine-dependent, and estimated evacuation duration is not a proof of optimality.

### Discrete-mathematics concepts: before and after

| Concept | Before these additions | After these additions |
|---|---|---|
| Hall's theorem | The console selected arbitrary uncovered rooms as a purported Hall witness, which could use the wrong side of the bipartite graph; the matching sides were also reversed. | Rooms are matched on the left to eligible marshals on the right. The witness is generated by alternating reachability from unmatched rooms, and its marshal neighborhood is checked against that room subset. |
| Pigeonhole principle | Only the aggregate exit-capacity lower bound was reported. | The report also states the generalized bound that some exit receives at least `ceil(people / exits)` under an assignment. |
| Inclusion-exclusion | The helper and report were specific to two exits. | A generic union-count helper handles any number of exit-access sets and checks its result against direct set union. |
| Edge-disjoint paths and cuts | No graph-resilience measure was reported. | Unit-capacity max-flow gives the edge-disjoint path count and a corresponding minimum corridor cut from the first room to each exit. |
| Time-expanded flow | No per-tick network model was available. | A time-expanded network estimates the earliest completion horizon under stated relaxed assumptions; it is an optimistic bound, not a policy-valid schedule. |
| Min-cost flow | Exit assignments were compared by brute force or a nearest-exit heuristic. | A successive-shortest-augmenting-path min-cost flow maximizes assigned occupants and then minimizes total shortest-path travel cost, respecting allowed exits and horizon-limited exit capacity. |
| Program correctness | Regression tests covered a few graph algorithms. | Tests now cover the new math routines, and route/wave invariants are checked in the regression suite. |

The added flow analyses intentionally have different scopes. The time-expanded model allows every room to use every exit and omits vertex-storage limits, so it can only provide an optimistic bound. The min-cost assignment respects room-to-exit permissions and exit throughput over its chosen horizon, but does not jointly enforce corridor capacities over time. Neither result is a complete crowd-flow schedule. The simpler max-flow/min-cut throughput diagnostic likewise relaxes room-specific exit permissions.

The regression tests exercise these implementation invariants: each planned route starts at its room, ends at an allowed reachable exit, and uses open corridors; adjacent conflict-graph vertices are assigned to different waves; and a reachable positive-population room eventually reaches zero remaining occupants in the simulation. These tests provide evidence for the implementation but are not a formal proof of every algorithm or input case.

## Testing

Run the Python regression tests:

```bash
python -m unittest -v
```

Compile-check the main Python module:

```bash
python -m py_compile main.py
```

To compile-check all Python files recursively:

```bash
python -c "import pathlib, py_compile; files=list(pathlib.Path('.').rglob('*.py')); [py_compile.compile(str(p), doraise=True) for p in files]; print(f'Compiled {len(files)} Python files')"
```

These checks do not replace end-to-end browser testing or validation against real building evacuation data.

## Known Limitations

- The simulator is a deterministic educational model, not a validated crowd or fire-safety model.
- It does not fully model smoke or fire propagation, individual movement variability, panic, counterflow, visibility, accessibility requirements, or empirically calibrated crowd-density relationships.
- Routing policies are heuristics. Results depend on the current graph, weights, capacities, scenario configuration, and simulation assumptions.
- Greedy graph coloring does not establish collision-free physical movement or globally optimal evacuation waves.
- The maximum-flow diagnostic is not a time-expanded crowd-flow simulation and must not be interpreted as certified real-world evacuation throughput.
- Travel-time and capacity values are model inputs unless explicitly calibrated against reliable data.
- The JavaScript interface and Python analytical application are educational implementations of related concepts; they do not form a distributed real-time emergency-control system.
- A schematic graph is not equivalent to a measured architectural floor plan. Real deployment would require verified building geometry, validated assumptions, and qualified safety review.

## Project Scope

EvacuateLab demonstrates how Discrete Mathematics and algorithmic techniques can be applied to a practical emergency-planning problem. Its primary focus is mathematical modelling, graph algorithms, optimization heuristics, simulation, and comparative analysis.

It is intended for academic exploration and demonstration, not operational emergency management.
