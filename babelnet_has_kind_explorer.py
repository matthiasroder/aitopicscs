#!/usr/bin/env python3
"""
BabelNet "Has-Kind" Relation Explorer
Recursively explores hyponym concepts using the "has-kind" relation from a starting BabelNet synset.
The "has-kind" relation represents hyponymy relationships (specific subtypes of a concept).
Allows configurable recursion depth and starting synset ID.
"""

import requests
import yaml
import json
import argparse
from typing import Set, List, Dict, Any, Tuple
from collections import defaultdict, deque


class BabelNetHasKindExplorer:
    def __init__(self, config_file: str = "babelnet_conf.yml"):
        """Initialize with API key from config file."""
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        self.api_key = config['RESTFUL_KEY']
        self.base_url = "https://babelnet.io/v9"
        self.cache = {}  # Simple cache to avoid duplicate API calls
    
    def get_synset(self, synset_id: str) -> Dict[str, Any]:
        """Retrieve synset details with caching."""
        if synset_id in self.cache:
            return self.cache[synset_id]
        
        url = f"{self.base_url}/getSynset"
        params = {
            "id": synset_id,
            "key": self.api_key
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        synset_data = response.json()
        self.cache[synset_id] = synset_data
        return synset_data
    
    def get_outgoing_edges(self, synset_id: str) -> List[Dict[str, Any]]:
        """Extract outgoing edges for a synset."""
        url = f"{self.base_url}/getOutgoingEdges"
        params = {
            "id": synset_id,
            "key": self.api_key
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def extract_has_kind_relations(self, edges: List[Dict[str, Any]]) -> List[str]:
        """Filter edges for 'has-kind' relations (hyponyms)."""
        has_kind_targets = []
        
        for edge in edges:
            pointer = edge.get("pointer", {})
            # Filter for exact "has-kind" relation (hyponymy)
            if pointer.get("shortName") == "has-kind":
                has_kind_targets.append(edge["target"])
        
        return has_kind_targets
    
    def get_synset_label(self, synset_data: Dict[str, Any]) -> str:
        """Extract the best English label for a synset."""
        senses = synset_data.get("senses", [])
        
        # Try to find English sense first
        for sense in senses:
            if sense.get("language") == "EN":
                properties = sense.get("properties", {})
                lemma = properties.get("simpleLemma") or properties.get("fullLemma")
                if lemma:
                    return lemma
        
        # Fallback to any available sense
        for sense in senses:
            properties = sense.get("properties", {})
            lemma = properties.get("simpleLemma") or properties.get("fullLemma")
            if lemma:
                return f"{lemma} ({sense.get('language', 'UNK')})"
        
        return synset_data.get("id", "Unknown")
    
    def explore_has_kind_recursive(self, starting_synset: str, max_depth: int = 3) -> Dict[str, Any]:
        """
        Recursively explore 'has kind' relations using breadth-first search.
        
        Args:
            starting_synset: BabelNet synset ID to start from (e.g., 'bn:00021494n')
            max_depth: Maximum recursion depth
            
        Returns:
            Dictionary containing the exploration tree and statistics
        """
        print(f"Starting exploration from: {starting_synset}")
        print(f"Maximum depth: {max_depth}")
        
        # Results structure
        exploration_tree = defaultdict(list)
        visited = set()
        synset_labels = {}
        depth_stats = defaultdict(int)
        
        # BFS queue: (synset_id, current_depth, parent_id)
        queue = deque([(starting_synset, 0, None)])
        visited.add(starting_synset)
        
        while queue:
            current_synset, current_depth, parent_id = queue.popleft()
            
            if current_depth > max_depth:
                continue
            
            try:
                print(f"Processing depth {current_depth}: {current_synset}")
                
                # Get synset details
                synset_data = self.get_synset(current_synset)
                label = self.get_synset_label(synset_data)
                synset_labels[current_synset] = label
                
                # Track statistics
                depth_stats[current_depth] += 1
                
                # Add to tree structure
                if parent_id:
                    exploration_tree[parent_id].append({
                        "synset_id": current_synset,
                        "label": label,
                        "depth": current_depth
                    })
                else:
                    # Root node
                    exploration_tree["root"] = {
                        "synset_id": current_synset,
                        "label": label,
                        "depth": current_depth
                    }
                
                # Don't explore further if we've reached max depth
                if current_depth >= max_depth:
                    continue
                
                # Get outgoing edges and filter for 'has-kind' (hyponyms)
                edges = self.get_outgoing_edges(current_synset)
                has_kind_targets = self.extract_has_kind_relations(edges)
                
                print(f"  Found {len(has_kind_targets)} 'has-kind' relations (hyponyms)")
                
                # Add unvisited targets to queue
                for target_id in has_kind_targets:
                    if target_id not in visited:
                        visited.add(target_id)
                        queue.append((target_id, current_depth + 1, current_synset))
                
            except Exception as e:
                print(f"Error processing {current_synset}: {e}")
                continue
        
        return {
            "starting_synset": starting_synset,
            "starting_label": synset_labels.get(starting_synset, "Unknown"),
            "max_depth": max_depth,
            "exploration_tree": dict(exploration_tree),
            "synset_labels": synset_labels,
            "depth_statistics": dict(depth_stats),
            "total_concepts_found": len(synset_labels)
        }
    
    def print_exploration_results(self, results: Dict[str, Any]):
        """Pretty print the exploration results."""
        print("\n" + "="*60)
        print("HAS-KIND RELATION EXPLORATION RESULTS (HYPONYMS)")
        print("="*60)
        
        print(f"Starting synset: {results['starting_synset']}")
        print(f"Starting label: {results['starting_label']}")
        print(f"Max depth: {results['max_depth']}")
        print(f"Total concepts found: {results['total_concepts_found']}")
        
        print("\nDepth Statistics:")
        for depth, count in sorted(results['depth_statistics'].items()):
            print(f"  Depth {depth}: {count} concepts")
        
        print("\nConcept Tree:")
        self._print_tree_recursive(results['exploration_tree'], results['synset_labels'], 0)
    
    def _print_tree_recursive(self, tree: Dict, labels: Dict, indent_level: int):
        """Recursively print the tree structure."""
        indent = "  " * indent_level
        
        if "root" in tree:
            root = tree["root"]
            print(f"{indent}• {root['label']} ({root['synset_id']})")
            
            # Print children
            for child in tree.get(root['synset_id'], []):
                print(f"{indent}  ├─ {child['label']} ({child['synset_id']})")
                # Recursively print grandchildren
                self._print_children_recursive(tree, child['synset_id'], labels, indent_level + 2)
    
    def _print_children_recursive(self, tree: Dict, parent_id: str, labels: Dict, indent_level: int):
        """Helper to recursively print children."""
        indent = "  " * indent_level
        children = tree.get(parent_id, [])
        
        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            connector = "└─" if is_last else "├─"
            print(f"{indent}{connector} {child['label']} ({child['synset_id']})")
            
            # Recursively print grandchildren
            if child['synset_id'] in tree:
                next_indent = indent_level + 1
                self._print_children_recursive(tree, child['synset_id'], labels, next_indent)


def main():
    """Main execution function with command line arguments."""
    parser = argparse.ArgumentParser(
        description="Explore BabelNet concepts using 'has kind' relations"
    )
    parser.add_argument(
        "synset_id", 
        help="Starting BabelNet synset ID (e.g., bn:00040680n for GPS)"
    )
    parser.add_argument(
        "--depth", "-d", 
        type=int, 
        default=2,
        help="Maximum recursion depth (default: 2)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file to save results as JSON"
    )
    
    args = parser.parse_args()
    
    explorer = BabelNetHasKindExplorer()
    
    try:
        results = explorer.explore_has_kind_recursive(
            starting_synset=args.synset_id,
            max_depth=args.depth
        )
        
        explorer.print_exploration_results(results)
        
        # Save results if output file specified
        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2)
            print(f"\nResults saved to: {args.output}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())