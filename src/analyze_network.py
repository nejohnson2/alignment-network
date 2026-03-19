"""Analyze co-authorship network: centrality, communities, paper importance.

Reads the co-authorship JSON from parse_bib.py and computes network metrics.
Saves results as CSV and JSON for the visualization step.
"""

import argparse
import json
import logging
from pathlib import Path

import community as community_louvain
import networkx as nx
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def build_graph(data: dict) -> nx.Graph:
    """Build a networkx graph from co-authorship data."""
    G = nx.Graph()

    for node in data["nodes"]:
        G.add_node(node["name"], paper_count=node["paper_count"], papers=node["papers"])

    for edge in data["edges"]:
        G.add_edge(
            edge["source"],
            edge["target"],
            weight=edge["weight"],
            papers=edge["papers"],
        )

    logger.info("Graph: %d nodes, %d edges", G.number_of_nodes(), G.number_of_edges())
    return G


def compute_author_metrics(G: nx.Graph) -> pd.DataFrame:
    """Compute centrality and connectivity metrics for each author."""
    degree_cent = nx.degree_centrality(G)
    betweenness_cent = nx.betweenness_centrality(G, weight="weight")
    closeness_cent = nx.closeness_centrality(G)
    # Eigenvector centrality per connected component (fails on disconnected graphs)
    eigenvector_cent = {}
    for component in nx.connected_components(G):
        subgraph = G.subgraph(component)
        if len(component) == 1:
            node = next(iter(component))
            eigenvector_cent[node] = 0.0
        else:
            ec = nx.eigenvector_centrality_numpy(subgraph, weight="weight")
            eigenvector_cent.update(ec)

    # Community detection (Louvain)
    partition = community_louvain.best_partition(G, weight="weight", random_state=42)

    rows = []
    for name in G.nodes():
        rows.append(
            {
                "author": name,
                "paper_count": G.nodes[name]["paper_count"],
                "degree": G.degree(name),
                "weighted_degree": G.degree(name, weight="weight"),
                "degree_centrality": round(degree_cent[name], 4),
                "betweenness_centrality": round(betweenness_cent[name], 4),
                "closeness_centrality": round(closeness_cent[name], 4),
                "eigenvector_centrality": round(eigenvector_cent[name], 4),
                "community": partition[name],
            }
        )

    df = pd.DataFrame(rows)

    # Composite importance score (normalized rank across metrics)
    for col in ["degree_centrality", "betweenness_centrality", "eigenvector_centrality", "paper_count"]:
        df[f"{col}_rank"] = df[col].rank(pct=True)

    df["importance_score"] = (
        df["degree_centrality_rank"] * 0.3
        + df["betweenness_centrality_rank"] * 0.3
        + df["eigenvector_centrality_rank"] * 0.2
        + df["paper_count_rank"] * 0.2
    )
    df["importance_score"] = df["importance_score"].round(4)

    # Drop temp rank columns
    df = df.drop(columns=[c for c in df.columns if c.endswith("_rank")])

    df = df.sort_values("importance_score", ascending=False).reset_index(drop=True)
    return df, partition


def compute_paper_metrics(data: dict, G: nx.Graph, author_df: pd.DataFrame) -> pd.DataFrame:
    """Compute paper-level importance metrics."""
    author_importance = dict(zip(author_df["author"], author_df["importance_score"]))

    rows = []
    for paper in data["papers"]:
        authors = paper["authors"]
        # Average author importance
        avg_importance = sum(author_importance.get(a, 0) for a in authors) / max(len(authors), 1)
        # Max author importance (proxy: paper with most central author)
        max_importance = max((author_importance.get(a, 0) for a in authors), default=0)
        # Number of cross-community edges this paper creates
        rows.append(
            {
                "key": paper["key"],
                "title": paper["title"],
                "year": paper["year"],
                "n_authors": paper["n_authors"],
                "avg_author_importance": round(avg_importance, 4),
                "max_author_importance": round(max_importance, 4),
            }
        )

    df = pd.DataFrame(rows)
    df = df.sort_values("avg_author_importance", ascending=False).reset_index(drop=True)
    return df


def main():
    parser = argparse.ArgumentParser(description="Analyze co-authorship network")
    parser.add_argument(
        "-i",
        "--input",
        default="analysis/coauthorship_data.json",
        help="Input co-authorship JSON",
    )
    parser.add_argument(
        "-o", "--output-dir", default="analysis", help="Output directory"
    )
    args = parser.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)

    G = build_graph(data)
    author_df, partition = compute_author_metrics(G)
    paper_df = compute_paper_metrics(data, G, author_df)

    # Save author metrics
    author_csv = out / "author_metrics.csv"
    author_df.to_csv(author_csv, index=False)
    logger.info("Saved author metrics to %s", author_csv)

    # Save paper metrics
    paper_csv = out / "paper_metrics.csv"
    paper_df.to_csv(paper_csv, index=False)
    logger.info("Saved paper metrics to %s", paper_csv)

    # Save graph + partition as JSON for visualization
    graph_data = {
        "nodes": [],
        "edges": data["edges"],
        "communities": {str(k): v for k, v in partition.items()},
    }
    for _, row in author_df.iterrows():
        graph_data["nodes"].append(row.to_dict())

    graph_json = out / "network_analysis.json"
    with open(graph_json, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)
    logger.info("Saved network analysis to %s", graph_json)

    # Print summary
    n_communities = len(set(partition.values()))
    logger.info("Found %d communities", n_communities)
    logger.info("\nTop 10 authors by importance score:")
    print(author_df[["author", "paper_count", "degree", "importance_score", "community"]].head(10).to_string(index=False))

    logger.info("\nPaper rankings:")
    print(paper_df[["title", "year", "n_authors", "avg_author_importance"]].to_string(index=False))


if __name__ == "__main__":
    main()
