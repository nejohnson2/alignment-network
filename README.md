# AI Alignment Co-authorship Network

Interactive visualization and analysis of co-authorship networks in AI alignment research, built from BibTeX citation data.

## Research Objectives

- Identify the most connected and influential authors in AI alignment
- Discover research communities/clusters and who bridges them
- Rank papers by the centrality of their author networks
- Provide an interactive tool for exploring the collaboration landscape

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Full pipeline
```bash
make all     # parse → analyze → visualize
make dev     # run pipeline and open visualization in browser
```

### Individual steps
```bash
make parse       # Parse .bib file → analysis/coauthorship_data.json
make analyze     # Compute metrics → analysis/author_metrics.csv, paper_metrics.csv
make visualize   # Generate HTML → visualizations/coauthorship_network.html
```

### Adding new papers
1. Add entries to `ai_alignment.bib` (Zotero export works directly)
2. Run `make dev` to regenerate everything

## Pipeline

| Step | Script | Input | Output |
|------|--------|-------|--------|
| Parse | `src/parse_bib.py` | `.bib` file | `analysis/coauthorship_data.json` |
| Analyze | `src/analyze_network.py` | coauthorship JSON | `analysis/author_metrics.csv`, `paper_metrics.csv`, `network_analysis.json` |
| Visualize | `src/visualize_network.py` | network analysis JSON | `visualizations/coauthorship_network.html` |

## Metrics

### Author metrics
- **Degree centrality**: fraction of all authors this person has co-authored with
- **Betweenness centrality**: how often this author lies on shortest paths between others (bridges between clusters)
- **Eigenvector centrality**: connected to other well-connected authors
- **Importance score**: weighted composite of the above + paper count

### Paper metrics
- **Average author importance**: mean importance score of all authors on the paper
- **Max author importance**: highest-importance author on the paper

## Visualization

The interactive HTML graph uses force-directed layout with:
- **Node size** scaled by importance score
- **Node color** by community (Louvain clustering)
- **Edge thickness** by number of co-authored papers
- **Hover tooltips** with full author stats
- **Filter menu** to explore by community

## Dependencies

- Python 3.11+
- bibtexparser, networkx, pyvis, python-louvain, pandas, scipy
