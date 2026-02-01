#!/usr/bin/env python3
"""
Main script for running DHT experiments comparing Chord and Pastry.

This script implements Project_1: Implementation and Experimental Evaluation of Basic DHTs
for the Decentralized Data Engineering and Technologies course.
"""

import argparse
import sys
from experiments.runner import ExperimentRunner
from experiments.plots import generate_all_plots
from dht.data_loader import create_sample_dataset, load_movies, lookup_popularity_concurrent, get_popular_movie_titles
from dht.chord import Chord
from dht.pastry import Pastry
import random


def run_basic_test():
    """Run a basic test to verify implementations work."""
    print("\n" + "="*60)
    print("BASIC FUNCTIONALITY TEST")
    print("="*60)

    # Create small dataset
    items = create_sample_dataset(100)
    keys = [title for title, _ in items]

    # Test Chord
    print("\nTesting Chord...")
    chord = Chord(m=8)
    node_ids = [i * 30 for i in range(10)]  # 10 nodes
    chord.build(node_ids, items[:50])

    # Test operations
    test_key = keys[0]
    print(f"  Lookup '{test_key}'...")
    values, hops = chord.lookup(test_key)
    print(f"    Found: {len(values) if values else 0} values, Hops: {hops}")

    print(f"  Insert new key...")
    hops = chord.insert("new_movie", items[0][1])
    print(f"    Hops: {hops}")

    print(f"  Join new node...")
    hops = chord.join(255)
    print(f"    Hops: {hops}")

    # Test Pastry
    print("\nTesting Pastry...")
    pastry = Pastry(m=8, b=2)
    pastry.build(node_ids, items[:50])

    print(f"  Lookup '{test_key}'...")
    values, hops = pastry.lookup(test_key)
    print(f"    Found: {len(values) if values else 0} values, Hops: {hops}")

    print(f"  Insert new key...")
    hops = pastry.insert("new_movie", items[0][1])
    print(f"    Hops: {hops}")

    print("\nBasic test completed successfully!")


def run_scalability_experiment(args):
    """Run scalability experiments."""
    print("\n" + "="*60)
    print("SCALABILITY EXPERIMENT")
    print("="*60)

    runner = ExperimentRunner(m=args.m, seed=args.seed)

    # Define node counts to test
    node_counts = args.nodes if args.nodes else [50, 100, 200, 500]

    # Run experiments
    results = runner.run_comparison_experiment(
        num_nodes_list=node_counts,
        num_items=args.items,
        num_operations=args.operations,
        use_real_data=args.use_real_data,
        data_file=args.data_file
    )

    # Save results
    output_file = args.output or "results/experiment_results.csv"
    runner.save_results(results, output_file)

    # Print summary
    runner.print_summary(results)

    # Generate plots if requested
    if not args.no_plots:
        generate_all_plots(output_file, "results")


def run_concurrent_popularity_lookup(args):
    """Run concurrent popularity lookup for K movies."""
    print("\n" + "="*60)
    print("CONCURRENT POPULARITY LOOKUP")
    print("="*60)

    # Load data
    if args.use_real_data and args.data_file:
        print(f"Loading movies from {args.data_file}...")
        items = load_movies(args.data_file, max_records=args.items)
    else:
        print(f"Creating synthetic dataset with {args.items} movies...")
        items = create_sample_dataset(args.items)

    # Get top K popular titles
    k = args.k_movies
    print(f"\nFinding top {k} popular movies...")
    popular_titles = get_popular_movie_titles(items, k)

    print(f"Top {k} titles:")
    for i, title in enumerate(popular_titles, 1):
        print(f"  {i}. {title}")

    # Test with Chord
    print(f"\n--- Testing Chord ---")
    chord = Chord(m=args.m)
    node_ids = [random.randint(0, 2**args.m - 1) for _ in range(args.num_nodes)]
    chord.build(node_ids, items)

    print(f"Looking up {k} movies concurrently...")
    results_chord, total_hops_chord = lookup_popularity_concurrent(chord, popular_titles)

    print(f"\nChord Results:")
    for title, popularity in results_chord.items():
        print(f"  {title}: popularity = {popularity:.2f}")
    print(f"  Total hops: {total_hops_chord}")
    print(f"  Average hops per lookup: {total_hops_chord / len(popular_titles):.2f}")

    # Test with Pastry
    print(f"\n--- Testing Pastry ---")
    pastry = Pastry(m=args.m, b=4)
    random.seed(args.seed)  # Reset seed for fair comparison
    node_ids = [random.randint(0, 2**args.m - 1) for _ in range(args.num_nodes)]
    pastry.build(node_ids, items)

    print(f"Looking up {k} movies concurrently...")
    results_pastry, total_hops_pastry = lookup_popularity_concurrent(pastry, popular_titles)

    print(f"\nPastry Results:")
    for title, popularity in results_pastry.items():
        print(f"  {title}: popularity = {popularity:.2f}")
    print(f"  Total hops: {total_hops_pastry}")
    print(f"  Average hops per lookup: {total_hops_pastry / len(popular_titles):.2f}")

    # Comparison
    print(f"\n--- Comparison ---")
    if total_hops_chord < total_hops_pastry:
        improvement = (total_hops_pastry - total_hops_chord) / total_hops_pastry * 100
        print(f"Chord is {improvement:.1f}% more efficient")
    else:
        improvement = (total_hops_chord - total_hops_pastry) / total_hops_chord * 100
        print(f"Pastry is {improvement:.1f}% more efficient")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='DHT Comparison: Chord vs Pastry',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run basic functionality test
  python main.py --test

  # Run scalability experiment with default settings
  python main.py --experiment scalability

  # Run with specific node counts
  python main.py --experiment scalability --nodes 100 200 500 1000

  # Run concurrent popularity lookup for top 10 movies
  python main.py --experiment popularity --k-movies 10 --num-nodes 100

  # Use real movie dataset (if available)
  python main.py --experiment scalability --use-real-data --data-file data/movies_dataset.csv

  # Generate plots from existing results
  python main.py --plot-only results/experiment_results.csv
        """
    )

    parser.add_argument('--test', action='store_true',
                       help='Run basic functionality test')

    parser.add_argument('--experiment', choices=['scalability', 'popularity'],
                       help='Type of experiment to run')

    parser.add_argument('--nodes', type=int, nargs='+',
                       help='List of node counts to test (e.g., 50 100 200)')

    parser.add_argument('--num-nodes', type=int, default=100,
                       help='Number of nodes for popularity experiment (default: 100)')

    parser.add_argument('--items', type=int, default=1000,
                       help='Number of items/movies to use (default: 1000)')

    parser.add_argument('--operations', type=int, default=500,
                       help='Number of operations per experiment (default: 500)')

    parser.add_argument('--k-movies', type=int, default=10,
                       help='Number of movies for concurrent popularity lookup (default: 10)')

    parser.add_argument('--m', type=int, default=16,
                       help='Number of bits in DHT identifier space (default: 16)')

    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed for reproducibility (default: 42)')

    parser.add_argument('--use-real-data', action='store_true',
                       help='Use real movie dataset instead of synthetic data')

    parser.add_argument('--data-file', type=str,
                       help='Path to movies CSV file')

    parser.add_argument('--output', type=str,
                       help='Output file for results (default: results/experiment_results.csv)')

    parser.add_argument('--no-plots', action='store_true',
                       help='Skip generating plots')

    parser.add_argument('--plot-only', type=str, metavar='CSV_FILE',
                       help='Generate plots from existing CSV results')

    args = parser.parse_args()

    # Handle plot-only mode
    if args.plot_only:
        generate_all_plots(args.plot_only, "results")
        return

    # Handle test mode
    if args.test:
        run_basic_test()
        return

    # Handle experiment mode
    if args.experiment == 'scalability':
        run_scalability_experiment(args)
    elif args.experiment == 'popularity':
        run_concurrent_popularity_lookup(args)
    else:
        parser.print_help()
        print("\nNo experiment specified. Use --test for basic test or --experiment for full experiments.")


if __name__ == "__main__":
    main()
