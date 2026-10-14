# EvacuateLab: Interactive Graph-Based Emergency Evacuation Simulation and Algorithm Comparison

## Abstract
State the problem, graph model, routing strategies, simulation assumptions, and the specific experiments performed. Do not claim real-world safety certification.

## 1. Problem definition
- What is represented by a node?
- What is represented by a corridor?
- What are corridor walking-time weights and capacities?
- What counts as a route failure?
- What is the objective being compared?

## 2. Mathematical model
Define the graph `G=(V,E)`, rooms `R`, exits `X`, occupant count `p(v)`, edge weight `w(e)`, edge capacity `c(e)`, and blocked-edge set `B`.

Document assumptions: undirected corridors, discrete release ticks, static population during a run, simplified group movement, and omitted real-world effects.

## 3. Algorithms and data structures
For each algorithm, provide pseudocode, correctness intuition, time/space complexity, input assumptions, and a hand-worked example:
- Adjacency-list graph representation
- Dijkstra shortest path
- Capacity-penalized routing heuristics
- Reachability using graph traversal
- Edmonds–Karp max-flow/min-cut diagnostic
- Conflict graph and greedy coloring
- Dynamic replanning after a blocked edge

Clearly separate algorithms implemented in the Python console modules from the browser-side demonstration implementation.

## 4. Application design
Include screenshots of the command center, inspector, animated run, event log, Algorithm Lab, and scenario import/export. Describe the division between UI, graph model, routing, simulation, and evaluation.

## 5. Experimental method
- Hardware/browser/Python version
- Scenario sizes and random seeds
- Number of repetitions
- Routing policy parameters
- Measurements: planner runtime, estimated model duration, reachable rooms, route count, and stranded population
- How identical inputs are ensured across comparisons

## 6. Results
Insert only measured results. Include the raw CSV files, charts, and an explanation of variability. A shorter duration on one map does not prove a strategy is generally superior.

## 7. Correctness and validation
Describe unit tests, disconnected graphs, blocked routes, duplicate edges, zero-population rooms, one-exit networks, and randomized scenario tests. State any known failures or limitations.

## 8. Limitations and ethics
This model is not a real evacuation guidance system. Discuss crowd behavior, smoke/fire spread, accessibility, code requirements, uncertainty, calibration, and why professional validation would be required.

## 9. Conclusion and future work
Summarize findings supported by the experiment. Potential future work: time-expanded networks, explicit flow conservation per time step, edge-disjoint route alternatives, accessibility constraints, and better crowd dynamics.

## Appendix
Pseudocode, complexity table, test cases, scenario JSON, benchmark CSV, and individual contribution statements.
