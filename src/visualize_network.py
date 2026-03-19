"""Generate interactive co-authorship network visualization using pyvis.

Reads analysis results and produces an HTML file with an interactive
force-directed graph. Completely separated from the analysis step.
"""

import argparse
import json
import logging
from pathlib import Path

import networkx as nx
from pyvis.network import Network

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Distinct colors for communities
COMMUNITY_COLORS = [
    "#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
    "#42d4f4", "#f032e6", "#bfef45", "#fabed4", "#469990",
    "#dcbeff", "#9A6324", "#800000", "#aaffc3", "#808000",
    "#000075", "#a9a9a9",
]

# Scaling factor for layout coordinates (higher = more spread)
LAYOUT_SCALE = 3000


def compute_positions(nodes: list[dict], edges: list[dict]) -> dict[str, tuple[float, float]]:
    """Pre-compute node positions using networkx spring layout."""
    G = nx.Graph()
    for node in nodes:
        G.add_node(node["author"])
    for edge in edges:
        G.add_edge(edge["source"], edge["target"], weight=edge["weight"])

    # Use weight reciprocal so strongly connected nodes cluster,
    # but clusters themselves repel each other
    for u, v, d in G.edges(data=True):
        d["distance"] = 1.0 / d["weight"]

    pos = nx.spring_layout(
        G,
        k=5.0,           # high repulsion between unconnected nodes
        iterations=300,
        scale=LAYOUT_SCALE,
        seed=42,
        weight="distance",
    )
    return pos


def build_visualization(analysis_path: str, output_path: str) -> None:
    """Build interactive pyvis network from analysis JSON."""
    with open(analysis_path, encoding="utf-8") as f:
        data = json.load(f)

    nodes = data["nodes"]
    edges = data["edges"]

    # Determine scaling ranges (min-max normalize importance)
    importance_vals = [n["importance_score"] for n in nodes]
    min_importance = min(importance_vals)
    max_importance = max(importance_vals)
    importance_range = max_importance - min_importance if max_importance != min_importance else 1.0
    max_weight = max(e["weight"] for e in edges) if edges else 1

    # Pre-compute positions so clusters are well separated
    positions = compute_positions(nodes, edges)

    net = Network(
        height="900px",
        width="100%",
        bgcolor="#1a1a2e",
        font_color="#e0e0e0",
        directed=False,
        cdn_resources="remote",
    )

    # Physics off — positions are pre-computed
    net.set_options("""
    {
        "physics": {
            "enabled": false
        },
        "interaction": {
            "hover": true,
            "tooltipDelay": 100,
            "zoomView": true,
            "navigationButtons": false
        },
        "nodes": {
            "borderWidth": 2,
            "borderWidthSelected": 4
        },
        "edges": {
            "smooth": {
                "type": "continuous"
            }
        }
    }
    """)

    # Add nodes with pre-computed x, y
    for node in nodes:
        name = node["author"]
        papers = node["paper_count"]
        importance = node["importance_score"]
        community = node["community"]
        degree = node["degree"]

        # Scale node size: 6-90 with min-max normalization
        norm = (importance - min_importance) / importance_range
        size = 6 + norm * 84

        color = COMMUNITY_COLORS[community % len(COMMUNITY_COLORS)]

        # Build hover tooltip
        tooltip = (
            f"{name}\n"
            f"Papers: {papers}\n"
            f"Co-authors: {degree}\n"
            f"Importance: {importance:.3f}\n"
            f"Betweenness: {node['betweenness_centrality']:.3f}\n"
            f"Community: {community}"
        )

        # Label: last name only
        last_name = name.split()[-1] if name.split() else name
        label = last_name

        x, y = positions[name]

        net.add_node(
            name,
            label=label,
            title=tooltip,
            size=size,
            color=color,
            font={"size": 16, "vadjust": -(size / 2 + 12)},
            x=x,
            y=y,
        )

    # Add edges
    for edge in edges:
        weight = edge["weight"]
        # Scale edge width: 1-8
        width = 1 + (weight / max(max_weight, 1)) * 7
        # Edge opacity by weight
        alpha = hex(int(100 + (weight / max(max_weight, 1)) * 155))[2:]
        edge_color = f"#cccccc{alpha}"

        paper_list = "\n".join(edge["papers"])
        title = f"{edge['source']} -- {edge['target']}\nPapers together: {weight}\n{paper_list}"

        net.add_edge(
            edge["source"],
            edge["target"],
            value=weight,
            width=width,
            title=title,
            color=edge_color,
        )

    net.save_graph(output_path)
    logger.info("Saved interactive visualization to %s", output_path)


def main():
    parser = argparse.ArgumentParser(description="Visualize co-authorship network")
    parser.add_argument(
        "-i",
        "--input",
        default="analysis/network_analysis.json",
        help="Input network analysis JSON",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="visualizations/coauthorship_network.html",
        help="Output HTML file",
    )
    args = parser.parse_args()

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    build_visualization(args.input, args.output)


if __name__ == "__main__":
    main()
