"""Plotting utilities for experiment results."""

import csv
import matplotlib.pyplot as plt
import pandas as pd
from typing import List, Dict
import os


def load_results(csv_file: str) -> pd.DataFrame:
    """Load experiment results from CSV file."""
    return pd.read_csv(csv_file)


def plot_hops_by_nodes(df: pd.DataFrame, output_dir: str = "results"):
    """
    Plot average hops vs number of nodes for each operation.

    Creates separate plots for each operation type.
    """
    os.makedirs(output_dir, exist_ok=True)

    operations = df['operation'].unique()

    for operation in operations:
        op_df = df[df['operation'] == operation]

        # Skip if no data
        if op_df.empty or op_df['total_ops'].sum() == 0:
            continue

        plt.figure(figsize=(10, 6))

        # Plot Chord
        chord_df = op_df[op_df['protocol'] == 'chord']
        if not chord_df.empty:
            plt.plot(chord_df['num_nodes'], chord_df['avg_hops'],
                    marker='o', label='Chord', linewidth=2, markersize=8)

        # Plot Pastry
        pastry_df = op_df[op_df['protocol'] == 'pastry']
        if not pastry_df.empty:
            plt.plot(pastry_df['num_nodes'], pastry_df['avg_hops'],
                    marker='s', label='Pastry', linewidth=2, markersize=8)

        plt.xlabel('Number of Nodes', fontsize=12)
        plt.ylabel('Average Hops', fontsize=12)
        plt.title(f'Average Hops vs Number of Nodes - {operation.upper()}', fontsize=14, fontweight='bold')
        plt.legend(fontsize=11)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        output_file = os.path.join(output_dir, f'hops_vs_nodes_{operation}.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Saved plot: {output_file}")
        plt.close()


def plot_all_operations_comparison(df: pd.DataFrame, output_dir: str = "results"):
    """
    Plot comparison of all operations in a single figure.

    Creates a multi-subplot figure showing Chord vs Pastry for all operations.
    """
    os.makedirs(output_dir, exist_ok=True)

    operations = [op for op in df['operation'].unique()
                 if df[df['operation'] == op]['total_ops'].sum() > 0]

    if not operations:
        print("No operations with data to plot")
        return

    # Create subplots
    n_ops = len(operations)
    n_cols = 3
    n_rows = (n_ops + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 5 * n_rows))
    if n_rows == 1:
        axes = axes.reshape(1, -1)

    for idx, operation in enumerate(operations):
        row = idx // n_cols
        col = idx % n_cols
        ax = axes[row, col]

        op_df = df[df['operation'] == operation]

        # Plot Chord
        chord_df = op_df[op_df['protocol'] == 'chord']
        if not chord_df.empty:
            ax.plot(chord_df['num_nodes'], chord_df['avg_hops'],
                   marker='o', label='Chord', linewidth=2, markersize=6)

        # Plot Pastry
        pastry_df = op_df[op_df['protocol'] == 'pastry']
        if not pastry_df.empty:
            ax.plot(pastry_df['num_nodes'], pastry_df['avg_hops'],
                   marker='s', label='Pastry', linewidth=2, markersize=6)

        ax.set_xlabel('Number of Nodes', fontsize=10)
        ax.set_ylabel('Average Hops', fontsize=10)
        ax.set_title(f'{operation.upper()}', fontsize=11, fontweight='bold')
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

    # Remove empty subplots
    for idx in range(len(operations), n_rows * n_cols):
        row = idx // n_cols
        col = idx % n_cols
        fig.delaxes(axes[row, col])

    plt.tight_layout()
    output_file = os.path.join(output_dir, 'all_operations_comparison.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved plot: {output_file}")
    plt.close()


def plot_performance_ratio(df: pd.DataFrame, output_dir: str = "results"):
    """
    Plot Chord/Pastry performance ratio for each operation.

    Ratio > 1 means Chord uses more hops (Pastry is better).
    Ratio < 1 means Pastry uses more hops (Chord is better).
    """
    os.makedirs(output_dir, exist_ok=True)

    operations = [op for op in df['operation'].unique()
                 if df[df['operation'] == op]['total_ops'].sum() > 0]

    if not operations:
        return

    plt.figure(figsize=(12, 6))

    for operation in operations:
        op_df = df[df['operation'] == operation]

        # Get Chord and Pastry data
        chord_df = op_df[op_df['protocol'] == 'chord'].sort_values('num_nodes')
        pastry_df = op_df[op_df['protocol'] == 'pastry'].sort_values('num_nodes')

        if len(chord_df) == len(pastry_df):
            ratios = chord_df['avg_hops'].values / (pastry_df['avg_hops'].values + 1e-10)
            plt.plot(chord_df['num_nodes'], ratios, marker='o', label=operation, linewidth=2)

    plt.axhline(y=1, color='black', linestyle='--', linewidth=1, alpha=0.5)
    plt.xlabel('Number of Nodes', fontsize=12)
    plt.ylabel('Performance Ratio (Chord hops / Pastry hops)', fontsize=12)
    plt.title('Chord vs Pastry Performance Ratio', fontsize=14, fontweight='bold')
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    output_file = os.path.join(output_dir, 'performance_ratio.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved plot: {output_file}")
    plt.close()


def plot_boxplot_comparison(df: pd.DataFrame, output_dir: str = "results"):
    """
    Create box plots comparing hop distributions for main operations.

    Note: This function expects raw hop data. For now, we'll use avg/min/max.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Filter for main operations
    main_ops = ['lookup', 'insert', 'delete', 'update']
    plot_df = df[df['operation'].isin(main_ops) & (df['total_ops'] > 0)]

    if plot_df.empty:
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Chord
    chord_df = plot_df[plot_df['protocol'] == 'chord']
    if not chord_df.empty:
        chord_data = [chord_df[chord_df['operation'] == op]['avg_hops'].values
                      for op in main_ops if op in chord_df['operation'].values]
        axes[0].boxplot([d for d in chord_data if len(d) > 0],
                       labels=[op for op in main_ops if op in chord_df['operation'].values])
        axes[0].set_title('Chord - Average Hops Distribution', fontweight='bold')
        axes[0].set_ylabel('Average Hops')
        axes[0].grid(True, alpha=0.3)

    # Pastry
    pastry_df = plot_df[plot_df['protocol'] == 'pastry']
    if not pastry_df.empty:
        pastry_data = [pastry_df[pastry_df['operation'] == op]['avg_hops'].values
                       for op in main_ops if op in pastry_df['operation'].values]
        axes[1].boxplot([d for d in pastry_data if len(d) > 0],
                       labels=[op for op in main_ops if op in pastry_df['operation'].values])
        axes[1].set_title('Pastry - Average Hops Distribution', fontweight='bold')
        axes[1].set_ylabel('Average Hops')
        axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    output_file = os.path.join(output_dir, 'hops_distribution.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved plot: {output_file}")
    plt.close()


def generate_all_plots(csv_file: str, output_dir: str = "results"):
    """
    Generate all plots from experiment results.

    Args:
        csv_file: Path to CSV file with results
        output_dir: Directory to save plots
    """
    print(f"\nGenerating plots from {csv_file}...")

    df = load_results(csv_file)

    print(f"Loaded {len(df)} result rows")

    # Generate all plots
    plot_hops_by_nodes(df, output_dir)
    plot_all_operations_comparison(df, output_dir)
    plot_performance_ratio(df, output_dir)
    plot_boxplot_comparison(df, output_dir)

    print(f"\nAll plots saved to {output_dir}/")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python plots.py <results.csv> [output_dir]")
        sys.exit(1)

    csv_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "results"

    generate_all_plots(csv_file, output_dir)
