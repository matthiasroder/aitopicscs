# AI Topics Computer Science - Research Toolkit

A comprehensive toolkit for exploring artificial intelligence topics and collecting academic research papers from multiple knowledge sources. This repository provides tools to discover AI subtopics using the Computer Science Ontology (CSO) and BabelNet, then systematically collect related research papers from arXiv.

## Overview

This toolkit enables researchers to:
1. **Explore AI taxonomies** using CSO and BabelNet knowledge graphs
2. **Generate comprehensive topic lists** with configurable depth
3. **Collect research papers** automatically from arXiv for discovered topics
4. **Build research databases** with deduplication and progress tracking

## Tools

### 📊 CSO Topic Explorer (`filter_ai_subtopics.py`)

Recursively explores the Computer Science Ontology to extract AI subtopics using breadth-first search.

```bash
# Get AI subtopics with 3 levels of depth
python filter_ai_subtopics.py artificial_intelligence --depth 3

# Explore machine learning topics
python filter_ai_subtopics.py machine_learning --depth 2 --output ml_topics.json

# Custom CSO file location
python filter_ai_subtopics.py neural_networks --csv data/CSO.3.4.1.csv --depth 2
```

**Parameters:**
- `starting_topic`: CSO topic ID (e.g., `artificial_intelligence`)
- `--depth, -d`: Recursion depth (default: 1)
- `--output, -o`: Save results as JSON
- `--csv, -c`: CSO CSV file path (default: `data/CSO.3.4.1.csv`)

### 🌐 BabelNet Concept Explorer (`babelnet_has_kind_explorer.py`)

Discovers semantic relationships using BabelNet's "has-kind" hyponym relations.

```bash
# Explore GPS concept subtypes
python babelnet_has_kind_explorer.py bn:00040680n --depth 2

# Save detailed exploration results
python babelnet_has_kind_explorer.py bn:00021494n --depth 3 --output results.json
```

**Parameters:**
- `synset_id`: BabelNet synset ID (required)
- `--depth, -d`: Maximum recursion depth (default: 2)
- `--output, -o`: Save results as JSON

### 📚 arXiv Paper Collector (`arxiv_collector.py`)

Systematically collects research papers from arXiv using topic keywords, with robust features for large-scale data collection.

```bash
# Start collection from generated topic file
python arxiv_collector.py subtopics_artificial_intelligence_depth_3.txt

# Resume interrupted collection
python arxiv_collector.py subtopics_artificial_intelligence_depth_3.txt

# Show progress summary
python arxiv_collector.py subtopics_artificial_intelligence_depth_3.txt --summary-only

# Custom database and rate limiting
python arxiv_collector.py ai_topics.txt --database ai_papers.db --delay 5.0
```

**Parameters:**
- `keywords_file`: Path to topic keywords file (required)
- `--database, -d`: SQLite database path (default: `arxiv_papers.db`)
- `--delay`: API request delay in seconds (default: 3.0)
- `--no-resume`: Start fresh instead of resuming
- `--summary-only`: Show progress and exit

**Key Features:**
- **Rate limiting**: Configurable delays between API requests
- **Deduplication**: Prevents duplicate papers across keywords
- **Resume capability**: Continue interrupted collections
- **Progress tracking**: Real-time progress with ETA calculations
- **Graceful shutdown**: Handle interruptions cleanly (Ctrl+C)
- **Comprehensive logging**: File and console logging
- **Batch processing**: Handles large result sets efficiently

## Workflow Example

Complete workflow for building an AI research database:

```bash
# 1. Generate comprehensive AI topic list
python filter_ai_subtopics.py artificial_intelligence --depth 3
# Creates: subtopics_artificial_intelligence_depth_3.txt

# 2. Collect papers for all topics
python arxiv_collector.py subtopics_artificial_intelligence_depth_3.txt

# 3. Check collection progress
python arxiv_collector.py subtopics_artificial_intelligence_depth_3.txt --summary-only

# 4. Explore semantic relationships (optional)
python babelnet_has_kind_explorer.py bn:00021494n --depth 2 --output ai_concepts.json
```

## Setup

### Prerequisites
- Python 3.6+
- Internet connection for API access

### Installation

1. **Clone repository:**
```bash
git clone <repository-url>
cd aitopicscs
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure BabelNet API** (optional, for BabelNet explorer):
```bash
# Create babelnet_conf.yml
echo "RESTFUL_KEY: 'your-api-key-here'" > babelnet_conf.yml
```

4. **Download CSO data** (if not included):
   - Place CSO.3.4.1.csv in the `data/` directory
   - Available from [Computer Science Ontology](https://cso.kmi.open.ac.uk/)

## Data Structure

### Generated Files
- `subtopics_<topic>_depth_<n>.txt`: Topic keyword lists
- `arxiv_papers.db`: SQLite database with collected papers
- `arxiv_collector.log`: Collection process logs
- `<topic>_exploration.json`: Detailed exploration results

### Database Schema
- **papers**: arXiv paper metadata (title, authors, abstract, etc.)
- **keywords**: Topic processing status and statistics
- **paper_keywords**: Many-to-many relationship mapping

## Research Applications

This toolkit supports various research scenarios:

- **Literature surveys**: Comprehensive paper collection for specific AI domains
- **Topic discovery**: Finding related concepts and subtopics
- **Research trend analysis**: Tracking publications across AI subspecialties
- **Dataset creation**: Building labeled datasets for research classification
- **Knowledge graph construction**: Mapping relationships between AI concepts

## Performance Notes

- **CSO exploration**: Fast local graph traversal
- **BabelNet exploration**: Rate-limited by API quotas
- **arXiv collection**: Respects API limits with configurable delays
- **Scalability**: Handles thousands of topics and papers efficiently

## Requirements

See `requirements.txt`:
- `requests>=2.28.0`: HTTP API calls
- `PyYAML>=6.0`: Configuration file parsing  
- `feedparser>=6.0.0`: arXiv RSS feed processing