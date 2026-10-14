# Team execution plan (4 members)

## Goal
Deliver a defensible educational simulation and demonstrate the data structures and algorithms through working code, reproducible test cases, and a short performance study.

## Member 1 — Graph model and routing
- Own `graph.py`, `algorithms.py` (Dijkstra, reachability, BFS/DFS extensions), and graph input validation.
- Add unit tests for disconnected rooms, equal-cost routes, blocked corridors, and invalid edges.
- Explain adjacency lists, weighted graphs, priority queues, and complexity.

## Member 2 — Optimization and mathematical model
- Own max-flow/min-cut, conflict graph, graph coloring, matching, and the written assumptions.
- Document which results are exact for the mathematical model and which are heuristic.
- Add small hand-verifiable examples and compare algorithm output to expected answers.

## Member 3 — Frontend and interaction
- Own `index.html`, `styles.css`, `app.js`, accessibility, responsive layout, graph editor, inspector, animation, import/export.
- Test node/edge CRUD, file import/export, keyboard access, small screens, and failure toggling.
- Keep labels honest: a model tick is not a calibrated minute, and a heuristic is not a proof of optimality.

## Member 4 — Simulation, scenarios and evaluation
- Own scenario generation, failure-injection test cases, benchmark protocol, CSV analysis and plots for the report.
- Run each routing policy on identical graphs with several seeds and multiple occupancy distributions.
- Report medians/means and variation where appropriate; do not select only favorable runs.

## Integration checkpoints
1. **Graph contract:** node IDs are unique; edges reference existing nodes; capacities are positive; walking-time weights are positive.
2. **Algorithm contract:** every returned route starts at the source, ends at an available exit, and uses only open edges.
3. **Simulation contract:** each occupant is in exactly one state (remaining, in transit, evacuated, or stranded); wave scheduling and re-planning are documented.
4. **Experiment contract:** compare the same graph/population for every strategy; preserve exported scenario JSON and CSV outputs.
5. **Presentation:** demo a normal run, a blocked corridor mid-run, an unreachable-room case, a benchmark, and a saved/exported scenario.

## Recommended demo sequence (5–7 minutes)
1. Load the reference campus and explain nodes, weighted corridors, and capacities.
2. Select a corridor and change its capacity; apply and inspect updated reachability/bottleneck information.
3. Run the animation and pause/resume it.
4. Run again with automatic incident injection and point out the re-planning log.
5. Open Algorithm Lab, run the three strategies, and export CSV.
6. Load the stress-test scenario, export JSON, and explain the modelling limitations.
