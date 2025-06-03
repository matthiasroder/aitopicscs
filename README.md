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
