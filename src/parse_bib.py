"""Parse .bib file and build co-authorship graph data.

Reads a BibTeX file, extracts authors per paper, deduplicates entries,
and saves structured data for downstream analysis.
"""

import argparse
import json
import logging
import re
from itertools import combinations
from pathlib import Path

import bibtexparser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def normalize_author(name: str) -> str:
    """Normalize author name to 'First Last' format, handling BibTeX conventions."""
    name = name.strip()
    if not name:
        return ""
    # BibTeX "Last, First" -> "First Last"
    if "," in name:
        parts = [p.strip() for p in name.split(",", 1)]
        name = f"{parts[1]} {parts[0]}"
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name)
    return name


def parse_bib(bib_path: str) -> list[dict]:
    """Parse a .bib file and return a list of paper dicts with normalized authors."""
    logger.info("Parsing %s", bib_path)
    with open(bib_path, encoding="utf-8") as f:
        bib_db = bibtexparser.load(f)

    papers = []
    seen_dois = set()

    for entry in bib_db.entries:
        # Skip entries without authors
        author_str = entry.get("author", "").strip()
        if not author_str:
            logger.warning("Skipping entry '%s' — no authors", entry.get("ID", "?"))
            continue

        # Deduplicate by DOI
        doi = entry.get("doi", "").strip()
        if doi:
            if doi in seen_dois:
                logger.info("Skipping duplicate DOI: %s", doi)
                continue
            seen_dois.add(doi)

        authors = [normalize_author(a) for a in author_str.split(" and ")]
        authors = [a for a in authors if a]  # drop blanks

        title = entry.get("title", "Untitled")
        # Strip BibTeX brace formatting
        title = re.sub(r"[{}]", "", title)

        year = entry.get("year", "n.d.")

        papers.append(
            {
                "key": entry["ID"],
                "title": title,
                "year": year,
                "authors": authors,
                "doi": doi,
                "n_authors": len(authors),
            }
        )

    logger.info("Parsed %d unique papers with authors", len(papers))
    return papers


def build_edge_list(papers: list[dict]) -> list[dict]:
    """Build weighted co-authorship edge list from papers."""
    edge_weights: dict[tuple[str, str], list[str]] = {}

    for paper in papers:
        for a, b in combinations(sorted(paper["authors"]), 2):
            key = (a, b)
            edge_weights.setdefault(key, []).append(paper["key"])

    edges = []
    for (a, b), paper_keys in edge_weights.items():
        edges.append(
            {
                "source": a,
                "target": b,
                "weight": len(paper_keys),
                "papers": paper_keys,
            }
        )

    logger.info("Built %d co-authorship edges", len(edges))
    return edges


def main():
    parser = argparse.ArgumentParser(description="Parse .bib and build co-authorship data")
    parser.add_argument("bib_file", help="Path to .bib file")
    parser.add_argument(
        "-o", "--output-dir", default="analysis", help="Output directory"
    )
    args = parser.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    papers = parse_bib(args.bib_file)
    edges = build_edge_list(papers)

    # Collect author -> papers mapping
    author_papers: dict[str, list[str]] = {}
    for paper in papers:
        for a in paper["authors"]:
            author_papers.setdefault(a, []).append(paper["key"])

    nodes = [
        {"name": name, "paper_count": len(pkeys), "papers": pkeys}
        for name, pkeys in author_papers.items()
    ]

    data = {"papers": papers, "nodes": nodes, "edges": edges}

    out_path = out / "coauthorship_data.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info("Saved co-authorship data to %s", out_path)
    logger.info("  %d authors, %d edges, %d papers", len(nodes), len(edges), len(papers))


if __name__ == "__main__":
    main()
