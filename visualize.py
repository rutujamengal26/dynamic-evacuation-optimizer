"""
visualize.py
-------------
Optional PNG export (needs matplotlib + networkx -- skips gracefully if
they aren't installed, never breaks the main pipeline). Two panels:

  left:  the building graph, node colour = evacuation wave (the actual
         output of the Welsh-Powell coloring in simulation.py), blocked
         corridors drawn dashed red.
  right: total people remaining in the building vs. time, from the
         discrete-tick simulation -- where it flattens is where the
         re-plan after a live corridor failure slowed things down.
"""

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import networkx as nx
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

WAVE_COLORS = ["#2ca02c", "#1f77b4", "#ff7f0e", "#9467bd", "#8c564b", "#17becf", "#e377c2"]


def export(graph, population, waves, history, exits, out_path="evacuation_diagram.png"):
    if not AVAILABLE:
        print("(skipping PNG export -- run `pip install matplotlib networkx` to enable it)")
        return None

    room_wave = {}
    for w, members in waves.items():
        for m in members:
            room_wave[m] = w

    G = nx.Graph()
    for u, v, d in graph.edges():
        G.add_edge(u, v, blocked=d["blocked"], capacity=d["capacity"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))

    pos = nx.spring_layout(G, seed=7)
    node_colors = []
    for n in G.nodes():
        if n in exits:
            node_colors.append("#d62728")
        elif n in room_wave:
            node_colors.append(WAVE_COLORS[room_wave[n] % len(WAVE_COLORS)])
        else:
            node_colors.append("#cccccc")

    open_edges = [(u, v) for u, v, d in G.edges(data=True) if not d["blocked"]]
    blocked_edges = [(u, v) for u, v, d in G.edges(data=True) if d["blocked"]]

    nx.draw_networkx_edges(G, pos, edgelist=open_edges, ax=ax1, width=1.6, edge_color="#888888")
    nx.draw_networkx_edges(G, pos, edgelist=blocked_edges, ax=ax1, width=2.2,
                            edge_color="#d62728", style="dashed")
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=800, ax=ax1,
                            edgecolors="black", linewidths=1)
    nx.draw_networkx_labels(G, pos, font_size=9, font_weight="bold", ax=ax1)
    ax1.set_title("Building graph -- node colour = evacuation wave\n"
                   "(red = exit, dashed red = blocked corridor)", fontsize=10)
    ax1.axis("off")

    ticks = [h[0] for h in history]
    remaining_total = [sum(h[2].values()) for h in history]
    ax2.plot(ticks, remaining_total, marker="o", color="#1f77b4", linewidth=2)
    ax2.set_xlabel("tick (minutes)")
    ax2.set_ylabel("people still inside")
    ax2.set_title("Occupancy over time\n(a flat/slower stretch = a live re-plan in progress)",
                   fontsize=10)
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
