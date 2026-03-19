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

    # Inject author search/highlight widget into the HTML
    _inject_search_widget(output_path)
    logger.info("Saved interactive visualization to %s", output_path)


def _inject_search_widget(html_path: str) -> None:
    """Inject a search box that highlights an author and their connections."""
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    widget_html = """
<div id="author-search" style="position:fixed;top:15px;left:15px;z-index:1000;
    background:rgba(30,30,60,0.95);padding:12px 16px;border-radius:8px;
    border:1px solid #555;font-family:sans-serif;color:#e0e0e0;min-width:280px;">
  <label for="searchBox" style="font-size:14px;font-weight:bold;display:block;margin-bottom:6px;">
    Search Author</label>
  <input id="searchBox" type="text" placeholder="Type a name..."
    style="width:100%;padding:8px 10px;font-size:14px;border:1px solid #666;
    border-radius:4px;background:#2a2a4a;color:#fff;outline:none;"
    list="authorList" autocomplete="off">
  <datalist id="authorList"></datalist>
  <div id="searchInfo" style="margin-top:8px;font-size:12px;color:#aaa;"></div>
  <button id="clearBtn" style="margin-top:6px;padding:4px 12px;font-size:12px;
    background:#444;color:#ddd;border:1px solid #666;border-radius:4px;cursor:pointer;
    display:none;" onclick="clearSearch()">Clear</button>
</div>

<script type="text/javascript">
(function() {
    // Wait for network to be ready
    var checkReady = setInterval(function() {
        if (typeof network !== 'undefined' && network !== null) {
            clearInterval(checkReady);
            initSearch();
        }
    }, 200);

    function initSearch() {
        var allNodes = network.body.data.nodes;
        var allEdges = network.body.data.edges;
        var nodeIds = allNodes.getIds();

        // Populate datalist
        var datalist = document.getElementById('authorList');
        nodeIds.sort().forEach(function(id) {
            var opt = document.createElement('option');
            opt.value = id;
            datalist.appendChild(opt);
        });

        // Store original styles
        var originalNodes = {};
        nodeIds.forEach(function(id) {
            var n = allNodes.get(id);
            originalNodes[id] = {color: n.color, opacity: 1.0, font: Object.assign({}, n.font)};
        });
        var originalEdges = {};
        allEdges.getIds().forEach(function(id) {
            var e = allEdges.get(id);
            originalEdges[id] = {color: e.color, width: e.width};
        });

        var searchBox = document.getElementById('searchBox');
        var searchInfo = document.getElementById('searchInfo');
        var clearBtn = document.getElementById('clearBtn');

        searchBox.addEventListener('input', function() {
            var query = searchBox.value.trim().toLowerCase();
            if (!query) { resetAll(); return; }

            // Find matching node
            var match = nodeIds.find(function(id) {
                return id.toLowerCase() === query;
            });
            if (!match) {
                // Partial match
                match = nodeIds.find(function(id) {
                    return id.toLowerCase().includes(query);
                });
            }
            if (!match) { resetAll(); searchInfo.textContent = 'No match'; return; }

            highlightAuthor(match);
        });

        function highlightAuthor(authorId) {
            var connEdges = allEdges.get().filter(function(e) {
                return e.from === authorId || e.to === authorId;
            });
            var neighborIds = new Set();
            neighborIds.add(authorId);
            connEdges.forEach(function(e) {
                neighborIds.add(e.from);
                neighborIds.add(e.to);
            });

            // Dim all nodes
            var nodeUpdates = nodeIds.map(function(id) {
                if (id === authorId) {
                    return {id: id, opacity: 1.0, borderWidth: 5,
                        color: {background: originalNodes[id].color, border: '#ffffff'}};
                } else if (neighborIds.has(id)) {
                    return {id: id, opacity: 1.0, color: originalNodes[id].color};
                } else {
                    return {id: id, opacity: 0.1,
                        color: {background: '#333', border: '#333'},
                        font: {color: 'rgba(200,200,200,0.15)'}};
                }
            });
            allNodes.update(nodeUpdates);

            // Dim all edges
            var connEdgeIds = new Set(connEdges.map(function(e) { return e.id; }));
            var edgeUpdates = allEdges.getIds().map(function(id) {
                if (connEdgeIds.has(id)) {
                    return {id: id, color: '#ffffff', width: originalEdges[id].width + 1};
                } else {
                    return {id: id, color: 'rgba(50,50,50,0.1)', width: 0.5};
                }
            });
            allEdges.update(edgeUpdates);

            searchInfo.textContent = authorId + ': ' + (neighborIds.size - 1) + ' co-authors';
            clearBtn.style.display = 'inline-block';

            // No zoom — keep full network view
        }

        function resetAll() {
            var nodeUpdates = nodeIds.map(function(id) {
                return {id: id, opacity: 1.0, borderWidth: 2,
                    color: originalNodes[id].color,
                    font: originalNodes[id].font};
            });
            allNodes.update(nodeUpdates);

            var edgeUpdates = allEdges.getIds().map(function(id) {
                return {id: id, color: originalEdges[id].color, width: originalEdges[id].width};
            });
            allEdges.update(edgeUpdates);

            searchInfo.textContent = '';
            clearBtn.style.display = 'none';
        }

        window.clearSearch = function() {
            searchBox.value = '';
            resetAll();
            network.fit({animation: {duration: 500}});
        };
    }
})();
</script>
"""

    # Insert before closing </body>
    html = html.replace("</body>", widget_html + "\n</body>")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)


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
