#!/usr/bin/env python3
"""
Quick script to generate Chord vs Pastry comparison plots.
This runs experiments and creates all the plots automatically.
"""

from experiments.runner import ExperimentRunner
from experiments.plots import generate_all_plots

def main():
    print("="*60)
    print("CHORD vs PASTRY COMPARISON")
    print("="*60)
    print()

    # Create experiment runner
    runner = ExperimentRunner(m=16, seed=42)

    # Run comparison with different node counts
    print("Running experiments with different node counts...")
    print("This will test: lookup, insert, delete, update, join, leave")
    print()

    # Test with various node counts
    node_counts = [50, 100, 200]

    results = runner.run_comparison_experiment(
        num_nodes_list=node_counts,
        num_items=1000,      # 1000 movies
        num_operations=500,  # 500 operations per test
        use_real_data=False  # Use synthetic data (faster)
    )

    # Save results
    output_file = "results/chord_vs_pastry_comparison.csv"
    runner.save_results(results, output_file)

    # Print summary
    runner.print_summary(results)

    # Generate all plots
    print("\nGenerating plots...")
    generate_all_plots(output_file, "results")

    print("\n" + "="*60)
    print("COMPLETE!")
    print("="*60)
    print()
    print("Results saved to:")
    print(f"  - CSV: {output_file}")
    print(f"  - Plots: results/*.png")
    print()
    print("View plots:")
    print("  - results/hops_vs_nodes_lookup.png")
    print("  - results/hops_vs_nodes_insert.png")
    print("  - results/hops_vs_nodes_delete.png")
    print("  - results/all_operations_comparison.png")
    print("  - results/performance_ratio.png")
    print()

if __name__ == "__main__":
    main()
