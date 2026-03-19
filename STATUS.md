# Status — 2026-03-19

## Completed
- Full pipeline: parse .bib → network analysis → interactive visualization
- 11 unique papers parsed (1 no-author entry skipped, 1 duplicate DOI removed)
- 139 authors, 1826 co-authorship edges, 5 communities detected
- Interactive pyvis HTML visualization with force-directed layout

## Key Findings
- Top authors by importance: Samuel R. Bowman (4 papers), Carson Denison (4), Ethan Perez (5 papers, highest count)
- Most important paper by author centrality: "Alignment faking in large language models" (Greenblatt et al. 2024)
- 5 distinct research communities identified via Louvain clustering

## What's Left
- Grow the .bib file with more papers and re-run
- Consider adding temporal analysis (how communities evolve over time)
- Could add keyword/topic overlay to the network
