# BabelNet Concept Exploration Tools

This repository contains Python scripts for exploring semantic relationships in BabelNet using their REST API.

## Scripts

### `babelnet_has_kind_explorer.py`
Recursively explores hyponym relationships using BabelNet's "has-kind" relations. Starting from any BabelNet synset ID, it discovers subtypes and specific categories with configurable recursion depth.

**Usage:**
```bash
# Explore GPS concept with depth 2
python babelnet_has_kind_explorer.py bn:00040680n --depth 2

# Save results to file
python babelnet_has_kind_explorer.py bn:00040680n --depth 3 --output results.json
```

**Parameters:**
- `synset_id`: Starting BabelNet synset ID (required)
- `--depth, -d`: Maximum recursion depth (default: 2)
- `--output, -o`: Output JSON file path (optional)

### `filter_ai_subtopics.py`
Recursively explores the Computer Science Ontology (CSO) knowledge graph to extract subtopics with configurable depth. Loads the CSO CSV file and uses breadth-first search to discover hierarchical relationships.

**Usage:**
```bash
# Get direct AI subtopics (depth 1)
python filter_ai_subtopics.py artificial_intelligence --depth 1

# Explore 2 levels deep
python filter_ai_subtopics.py artificial_intelligence --depth 2

# Explore any topic with custom depth and save results
python filter_ai_subtopics.py machine_learning --depth 3 --output ml_exploration.json
```

**Parameters:**
- `starting_topic`: Topic ID to start from (e.g., artificial_intelligence)
- `--depth, -d`: Maximum recursion depth (default: 1)
- `--output, -o`: Output JSON file path (optional)
- `--csv, -c`: Path to CSO CSV file (default: data/CSO.3.4.1.csv)

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure your BabelNet API key in `babelnet_conf.yml`:
```yaml
RESTFUL_KEY: 'your-api-key-here'
```

## Requirements
- Python 3.6+
- Valid BabelNet API key
- Internet connection for API calls
