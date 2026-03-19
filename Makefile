.PHONY: all parse analyze visualize clean dev

BIB_FILE := ai_alignment.bib
VENV := .venv/bin/python

# Full pipeline
all: parse analyze visualize

# Step 1: Parse .bib and build co-authorship data
parse:
	$(VENV) src/parse_bib.py $(BIB_FILE)

# Step 2: Compute network metrics and communities
analyze: parse
	$(VENV) src/analyze_network.py

# Step 3: Generate interactive visualization
visualize: analyze
	$(VENV) src/visualize_network.py

# Dev: run full pipeline and open visualization
dev: all
	open visualizations/coauthorship_network.html

# Clean generated files
clean:
	rm -rf analysis/ visualizations/
