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

### `arxiv_collector.py`
Collects arXiv papers for AI topics by querying the arXiv API for each keyword from CSO subtopics. Stores results in SQLite database with deduplication, rate limiting, and resume capability.

**Usage:**
```bash
# Start collection from keywords file
python arxiv_collector.py subtopics_artificial_intelligence_depth_3.txt

# Resume interrupted collection
python arxiv_collector.py subtopics_artificial_intelligence_depth_3.txt

# Show progress summary only
python arxiv_collector.py subtopics_artificial_intelligence_depth_3.txt --summary-only

# Custom settings
python arxiv_collector.py subtopics_artificial_intelligence_depth_3.txt --delay 5.0 --database my_papers.db
```

**Parameters:**
- `keywords_file`: Path to keywords file (required)
- `--database, -d`: SQLite database path (default: arxiv_papers.db)
- `--delay`: Delay between API requests in seconds (default: 3.0)
- `--no-resume`: Start fresh instead of resuming from existing database
- `--summary-only`: Show progress summary and exit

**Features:**
- Rate limiting (3+ second delays between requests)
- Deduplication by arXiv ID across keywords
- Resume capability for interrupted collections
- Progress tracking with ETA calculations
- Graceful shutdown handling (Ctrl+C)
- Comprehensive logging to file and console

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
