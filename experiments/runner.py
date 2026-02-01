"""Experiment runner for comparing Chord and Pastry."""

import time
import random
import csv
from typing import List, Dict, Any, Tuple
from dht.chord import Chord
from dht.pastry import Pastry
from dht.data_loader import Movie, create_sample_dataset, load_movies
from experiments.workload import WorkloadGenerator, Operation, OperationType


class ExperimentResult:
    """Store results of a single experiment."""

    def __init__(self, protocol: str, operation: str, num_nodes: int, num_items: int):
        self.protocol = protocol
        self.operation = operation
        self.num_nodes = num_nodes
        self.num_items = num_items
        self.hops_list: List[int] = []
        self.latency_list: List[float] = []

    def add_measurement(self, hops: int, latency: float = 0.0):
        """Add a measurement."""
        self.hops_list.append(hops)
        self.latency_list.append(latency)

    def get_stats(self) -> Dict[str, float]:
        """Calculate statistics."""
        if not self.hops_list:
            return {
                'avg_hops': 0,
                'max_hops': 0,
                'min_hops': 0,
                'total_ops': 0
            }

        return {
            'avg_hops': sum(self.hops_list) / len(self.hops_list),
            'max_hops': max(self.hops_list),
            'min_hops': min(self.hops_list),
            'total_ops': len(self.hops_list),
            'avg_latency': sum(self.latency_list) / len(self.latency_list) if self.latency_list else 0
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV export."""
        stats = self.get_stats()
        return {
            'protocol': self.protocol,
            'operation': self.operation,
            'num_nodes': self.num_nodes,
            'num_items': self.num_items,
            **stats
        }


class ExperimentRunner:
    """Run experiments comparing Chord and Pastry."""

    def __init__(self, m: int = 16, seed: int = 42):
        """
        Initialize experiment runner.

        Args:
            m: Number of bits in identifier space
            seed: Random seed for reproducibility
        """
        self.m = m
        self.seed = seed
        self.workload_gen = WorkloadGenerator(seed=seed)
        random.seed(seed)

    def run_single_experiment(
        self,
        dht_type: str,
        num_nodes: int,
        items: List[Tuple[str, Movie]],
        operations: List[Operation]
    ) -> Dict[str, ExperimentResult]:
        """
        Run a single experiment with given DHT type and workload.

        Returns:
            Dictionary mapping operation type to ExperimentResult
        """
        print(f"Running {dht_type} with {num_nodes} nodes, {len(items)} items, {len(operations)} operations...")

        # Create DHT
        if dht_type == "Chord":
            dht = Chord(m=self.m)
        elif dht_type == "Pastry":
            dht = Pastry(m=self.m, b=4)
        else:
            raise ValueError(f"Unknown DHT type: {dht_type}")

        # Generate node IDs
        node_ids = [random.randint(0, 2**self.m - 1) for _ in range(num_nodes)]

        # Build DHT
        print(f"  Building {dht_type}...")
        build_start = time.time()
        dht.build(node_ids, items)
        build_time = time.time() - build_start
        print(f"  Build completed in {build_time:.2f}s")

        # Initialize results
        results = {}
        for op_type in OperationType:
            results[op_type.value] = ExperimentResult(
                protocol=dht_type,
                operation=op_type.value,
                num_nodes=num_nodes,
                num_items=len(items)
            )

        # Execute operations
        print(f"  Executing {len(operations)} operations...")
        for i, op in enumerate(operations):
            if i % 100 == 0 and i > 0:
                print(f"    Progress: {i}/{len(operations)}")

            start_time = time.time()
            hops = 0

            try:
                if op.op_type == OperationType.LOOKUP:
                    _, hops = dht.lookup(op.key)

                elif op.op_type == OperationType.INSERT:
                    # If value is a string, use first item's Movie object structure
                    # Otherwise use the provided value
                    if isinstance(op.value, str):
                        if items:
                            # Use a Movie object from items
                            insert_value = items[0][1]
                        else:
                            insert_value = op.value
                    else:
                        insert_value = op.value
                    hops = dht.insert(op.key, insert_value)

                elif op.op_type == OperationType.DELETE:
                    hops = dht.delete(op.key)

                elif op.op_type == OperationType.UPDATE:
                    # Same fix for update
                    if isinstance(op.value, str):
                        if items:
                            update_value = [items[0][1]]
                        else:
                            update_value = [op.value]
                    else:
                        update_value = op.value if isinstance(op.value, list) else [op.value]
                    hops = dht.update(op.key, update_value)

                elif op.op_type == OperationType.JOIN:
                    hops = dht.join(op.node_id)

                elif op.op_type == OperationType.LEAVE:
                    current_nodes = dht.get_all_nodes()
                    if current_nodes and op.node_id in current_nodes:
                        hops = dht.leave(op.node_id)

                latency = time.time() - start_time
                results[op.op_type.value].add_measurement(hops, latency)

            except Exception as e:
                print(f"    Error executing {op.op_type.value}: {e}")

        print(f"  {dht_type} experiment completed")
        return results

    def run_comparison_experiment(
        self,
        num_nodes_list: List[int],
        num_items: int = 1000,
        num_operations: int = 500,
        use_real_data: bool = False,
        data_file: str = None
    ) -> List[Dict[str, Any]]:
        """
        Run comparison experiments for different numbers of nodes.

        Args:
            num_nodes_list: List of node counts to test
            num_items: Number of items to insert
            num_operations: Number of operations per experiment
            use_real_data: Whether to use real movie data
            data_file: Path to movies CSV file

        Returns:
            List of result dictionaries
        """
        all_results = []

        # Load data
        if use_real_data and data_file:
            print(f"Loading movies from {data_file}...")
            items = load_movies(data_file, max_records=num_items)
            if not items:
                print("Failed to load data, using synthetic data instead")
                items = create_sample_dataset(num_items)
        else:
            print(f"Creating synthetic dataset with {num_items} movies...")
            items = create_sample_dataset(num_items)

        # Extract keys for workload generation
        keys = [title for title, _ in items[:num_items]]

        # Generate workload (same for both protocols)
        print(f"Generating workload with {num_operations} operations...")
        operations = self.workload_gen.generate_mixed_workload(num_operations, keys)

        # Run experiments for each node count
        for num_nodes in num_nodes_list:
            print(f"\n{'='*60}")
            print(f"Testing with {num_nodes} nodes")
            print(f"{'='*60}")

            # Reset random seed for reproducibility
            random.seed(self.seed)

            # Test Chord
            chord_results = self.run_single_experiment("Chord", num_nodes, items, operations)

            # Reset random seed again
            random.seed(self.seed)

            # Test Pastry
            pastry_results = self.run_single_experiment("Pastry", num_nodes, items, operations)

            # Collect results
            for op_type in OperationType:
                chord_stats = chord_results[op_type.value].to_dict()
                pastry_stats = pastry_results[op_type.value].to_dict()

                all_results.append(chord_stats)
                all_results.append(pastry_stats)

        return all_results

    def run_scalability_test(
        self,
        node_counts: List[int] = None,
        items_per_test: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Test scalability by varying number of nodes.

        Args:
            node_counts: List of node counts to test (default: [50, 100, 200, 500])
            items_per_test: Number of items per test

        Returns:
            List of result dictionaries
        """
        if node_counts is None:
            node_counts = [50, 100, 200, 500]

        print(f"\n{'='*60}")
        print("SCALABILITY TEST")
        print(f"{'='*60}")

        return self.run_comparison_experiment(
            num_nodes_list=node_counts,
            num_items=items_per_test,
            num_operations=500
        )

    def save_results(self, results: List[Dict[str, Any]], output_file: str):
        """Save results to CSV file."""
        if not results:
            print("No results to save")
            return

        print(f"\nSaving results to {output_file}...")

        with open(output_file, 'w', newline='') as f:
            fieldnames = results[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            writer.writeheader()
            for result in results:
                writer.writerow(result)

        print(f"Results saved successfully")

    def print_summary(self, results: List[Dict[str, Any]]):
        """Print summary of results."""
        print(f"\n{'='*60}")
        print("EXPERIMENT SUMMARY")
        print(f"{'='*60}")

        # Group by operation and num_nodes
        by_operation = {}
        for result in results:
            op = result['operation']
            nodes = result['num_nodes']
            protocol = result['protocol']

            key = (op, nodes)
            if key not in by_operation:
                by_operation[key] = {}

            by_operation[key][protocol] = result

        # Print comparison
        for (op, nodes), protocols in sorted(by_operation.items()):
            if 'Chord' in protocols and 'Pastry' in protocols:
                chord = protocols['Chord']
                pastry = protocols['Pastry']

                if chord['total_ops'] > 0 and pastry['total_ops'] > 0:
                    print(f"\nOperation: {op}, Nodes: {nodes}")
                    print(f"  Chord:  avg_hops={chord['avg_hops']:.2f}, "
                          f"total_ops={chord['total_ops']}")
                    print(f"  Pastry: avg_hops={pastry['avg_hops']:.2f}, "
                          f"total_ops={pastry['total_ops']}")

                    if chord['avg_hops'] > 0:
                        improvement = ((chord['avg_hops'] - pastry['avg_hops']) /
                                      chord['avg_hops'] * 100)
                        if improvement > 0:
                            print(f"  Pastry is {improvement:.1f}% better")
                        else:
                            print(f"  Chord is {-improvement:.1f}% better")
