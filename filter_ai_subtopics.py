#!/usr/bin/env python3
"""
Recursively explore CSO knowledge graph to extract subtopics with configurable depth.
"""

import csv
import argparse
import json
from collections import defaultdict, deque
from typing import Dict, Set, List, Tuple

def extract_topic_name(uri):
    """Extract clean topic name from CSO URI."""
    # Extract the part after the last '/'
    topic = uri.split('/')[-1].rstrip('>')
    # Replace underscores with spaces
    return topic.replace('_', ' ')

def extract_topic_id(uri):
    """Extract topic ID from CSO URI."""
    return uri.split('/')[-1].rstrip('>')

def load_cso_graph(csv_file="data/CSO.3.4.1.csv"):
    """Load CSO knowledge graph into memory for efficient querying."""
    print("Loading CSO knowledge graph...")
    
    # Graph structure: topic_id -> list of child topic_ids
    super_topic_graph = defaultdict(list)
    topic_names = {}
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        
        for row in reader:
            if len(row) != 3:
                continue
                
            subject, predicate, obj = row
            
            # Only process superTopicOf relationships
            if "superTopicOf" in predicate:
                parent_id = extract_topic_id(subject)
                child_id = extract_topic_id(obj)
                
                # Build graph: parent -> children
                super_topic_graph[parent_id].append(child_id)
                
                # Store topic names
                topic_names[parent_id] = extract_topic_name(subject)
                topic_names[child_id] = extract_topic_name(obj)
    
    print(f"Loaded {len(super_topic_graph)} parent topics with {sum(len(children) for children in super_topic_graph.values())} relationships")
    return super_topic_graph, topic_names

def explore_subtopics_recursive(starting_topic: str, max_depth: int, graph: Dict, topic_names: Dict):
    """
    Recursively explore subtopics using breadth-first search.
    
    Args:
        starting_topic: Topic ID to start from (e.g., 'artificial_intelligence')
        max_depth: Maximum recursion depth
        graph: Super-topic graph (parent -> children)
        topic_names: Mapping of topic IDs to human-readable names
        
    Returns:
        Dictionary containing the exploration tree and statistics
    """
    print(f"Starting exploration from: {starting_topic}")
    print(f"Maximum depth: {max_depth}")
    
    # Results structure
    exploration_tree = defaultdict(list)
    visited = set()
    depth_stats = defaultdict(int)
    all_subtopics = set()
    
    # BFS queue: (topic_id, current_depth, parent_id)
    queue = deque([(starting_topic, 0, None)])
    visited.add(starting_topic)
    
    while queue:
        current_topic, current_depth, parent_id = queue.popleft()
        
        if current_depth > max_depth:
            continue
        
        # Track statistics
        depth_stats[current_depth] += 1
        all_subtopics.add(current_topic)
        
        # Get human-readable name
        topic_name = topic_names.get(current_topic, current_topic)
        
        # Add to tree structure
        if parent_id:
            exploration_tree[parent_id].append({
                "topic_id": current_topic,
                "topic_name": topic_name,
                "depth": current_depth
            })
        else:
            # Root node
            exploration_tree["root"] = {
                "topic_id": current_topic,
                "topic_name": topic_name,
                "depth": current_depth
            }
        
        print(f"Depth {current_depth}: {topic_name} ({len(graph.get(current_topic, []))} children)")
        
        # Don't explore further if we've reached max depth
        if current_depth >= max_depth:
            continue
        
        # Get children (subtopics)
        children = graph.get(current_topic, [])
        
        # Add unvisited children to queue
        for child_id in children:
            if child_id not in visited:
                visited.add(child_id)
                queue.append((child_id, current_depth + 1, current_topic))
    
    return {
        "starting_topic": starting_topic,
        "starting_name": topic_names.get(starting_topic, starting_topic),
        "max_depth": max_depth,
        "exploration_tree": dict(exploration_tree),
        "depth_statistics": dict(depth_stats),
        "all_subtopics": list(all_subtopics),
        "total_topics_found": len(all_subtopics)
    }

def print_exploration_results(results: Dict):
    """Pretty print the exploration results."""
    print("\n" + "="*60)
    print("CSO SUBTOPIC EXPLORATION RESULTS")
    print("="*60)
    
    print(f"Starting topic: {results['starting_topic']}")
    print(f"Starting name: {results['starting_name']}")
    print(f"Max depth: {results['max_depth']}")
    print(f"Total topics found: {results['total_topics_found']}")
    
    print("\nDepth Statistics:")
    for depth, count in sorted(results['depth_statistics'].items()):
        print(f"  Depth {depth}: {count} topics")
    
    print("\nAll Subtopics (alphabetical):")
    subtopic_names = []
    for topic_id in results['all_subtopics']:
        # Find the name in the exploration tree
        name = find_topic_name_in_tree(topic_id, results['exploration_tree'])
        if name:
            subtopic_names.append(name)
    
    for i, name in enumerate(sorted(set(subtopic_names)), 1):
        print(f"{i:3d}. {name}")

def find_topic_name_in_tree(topic_id: str, tree: Dict) -> str:
    """Helper to find topic name in exploration tree."""
    if "root" in tree and tree["root"]["topic_id"] == topic_id:
        return tree["root"]["topic_name"]
    
    for parent_id, children in tree.items():
        if parent_id == "root":
            continue
        for child in children:
            if child["topic_id"] == topic_id:
                return child["topic_name"]
    return topic_id

def main():
    """Main execution function with command line arguments."""
    parser = argparse.ArgumentParser(
        description="Recursively explore CSO subtopics with configurable depth"
    )
    parser.add_argument(
        "starting_topic", 
        help="Starting topic ID (e.g., artificial_intelligence)"
    )
    parser.add_argument(
        "--depth", "-d", 
        type=int, 
        default=1,
        help="Maximum recursion depth (default: 1)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file to save results as JSON"
    )
    parser.add_argument(
        "--csv", "-c",
        default="data/CSO.3.4.1.csv",
        help="Path to CSO CSV file (default: data/CSO.3.4.1.csv)"
    )
    
    args = parser.parse_args()
    
    try:
        # Load the knowledge graph
        graph, topic_names = load_cso_graph(args.csv)
        
        # Explore subtopics
        results = explore_subtopics_recursive(
            starting_topic=args.starting_topic,
            max_depth=args.depth,
            graph=graph,
            topic_names=topic_names
        )
        
        print_exploration_results(results)
        
        # Save results if output file specified
        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2)
            print(f"\nResults saved to: {args.output}")
        
        # Also save a simple text list
        output_file = f"subtopics_{args.starting_topic}_depth_{args.depth}.txt"
        subtopic_names = []
        for topic_id in results['all_subtopics']:
            name = find_topic_name_in_tree(topic_id, results['exploration_tree'])
            if name:
                subtopic_names.append(name)
        
        with open(output_file, "w") as f:
            for name in sorted(set(subtopic_names)):
                f.write(f"{name}\n")
        
        print(f"Subtopic list saved to: {output_file}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())