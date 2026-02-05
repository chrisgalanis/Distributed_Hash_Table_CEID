"""Orchestrator for distributed DHT experiments."""

import requests
import time
import random
from typing import Dict, List, Tuple
import argparse
import logging

from dht.data_loader import create_sample_dataset
from dht.common import hash_key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DistributedOrchestrator:
    """
    Orchestrates distributed DHT experiments.
    Initializes nodes, loads data, and runs experiments.
    """

    def __init__(self, node_addresses: Dict[int, str], protocol: str, m: int = 16,
                 internal_addresses: Dict[int, str] = None):
        """
        Initialize orchestrator.

        Args:
            node_addresses: Dict mapping node_id -> "host:port" (for orchestrator to reach nodes)
            protocol: "chord" or "pastry"
            m: Bits in identifier space
            internal_addresses: Dict mapping node_id -> internal address (for nodes to reach each other)
                               If None, uses node_addresses
        """
        self.node_addresses = node_addresses
        self.internal_addresses = internal_addresses or node_addresses
        self.protocol = protocol
        self.m = m
        self.timeout = 10

    def check_health(self) -> Dict[int, bool]:
        """Check health of all nodes."""
        logger.info("Checking node health...")
        health_status = {}

        for node_id, address in self.node_addresses.items():
            try:
                url = f"http://{address}/health"
                response = requests.get(url, timeout=self.timeout)
                health_status[node_id] = response.status_code == 200
                logger.info(f"Node {node_id} at {address}: {'OK' if health_status[node_id] else 'FAIL'}")
            except Exception as e:
                logger.error(f"Node {node_id} at {address}: UNREACHABLE - {e}")
                health_status[node_id] = False

        return health_status

    def initialize_nodes(self):
        """Initialize DHT routing structures on all nodes."""
        logger.info(f"Initializing {self.protocol.upper()} nodes...")

        if self.protocol == "chord":
            self._initialize_chord()
        elif self.protocol == "pastry":
            self._initialize_pastry()

        logger.info("Node initialization complete")

    def _initialize_chord(self):
        """Initialize Chord ring."""
        # Sort nodes by ID
        sorted_nodes = sorted(self.node_addresses.keys())
        n = len(sorted_nodes)

        for i, node_id in enumerate(sorted_nodes):
            # Calculate successor and predecessor
            successor = sorted_nodes[(i + 1) % n]
            predecessor = sorted_nodes[(i - 1) % n]

            # Build finger table
            finger_table = []
            for k in range(self.m):
                start = (node_id + 2 ** k) % (2 ** self.m)
                # Find successor of start
                finger = self._find_successor_static(start, sorted_nodes)
                finger_table.append(finger)

            # Send initialization to node
            url = f"http://{self.node_addresses[node_id]}/init"
            payload = {
                'successor': successor,
                'predecessor': predecessor,
                'finger_table': finger_table,
                'node_registry': {str(nid): addr for nid, addr in self.internal_addresses.items()}
            }

            try:
                response = requests.post(url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                logger.info(f"Initialized Chord node {node_id}")
            except Exception as e:
                logger.error(f"Failed to initialize node {node_id}: {e}")

    def _initialize_pastry(self):
        """Initialize Pastry nodes."""
        all_nodes = list(self.node_addresses.keys())

        for node_id in all_nodes:
            url = f"http://{self.node_addresses[node_id]}/init"
            payload = {
                'all_nodes': all_nodes,
                'node_registry': {str(nid): addr for nid, addr in self.internal_addresses.items()}
            }

            try:
                response = requests.post(url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                logger.info(f"Initialized Pastry node {node_id}")
            except Exception as e:
                logger.error(f"Failed to initialize node {node_id}: {e}")

    def _find_successor_static(self, target_id: int, sorted_nodes: List[int]) -> int:
        """Find successor during static initialization."""
        for nid in sorted_nodes:
            if nid >= target_id:
                return nid
        return sorted_nodes[0]

    def load_data(self, items: List[Tuple[str, any]]):
        """Load data into DHT."""
        logger.info(f"Loading {len(items)} items into DHT...")

        for i, (key, value) in enumerate(items):
            if i % 100 == 0 and i > 0:
                logger.info(f"Loaded {i}/{len(items)} items...")

            # Find responsible node
            key_id = hash_key(key, self.m)
            responsible_node = self._find_responsible_node(key_id)

            # Store on responsible node
            url = f"http://{self.node_addresses[responsible_node]}/store"
            payload = {
                'key': key,
                'value': self._serialize_value(value)
            }

            try:
                requests.post(url, json=payload, timeout=self.timeout)
            except Exception as e:
                logger.error(f"Failed to store key {key} on node {responsible_node}: {e}")

        logger.info(f"Data loading complete")

    def _find_responsible_node(self, key_id: int) -> int:
        """Find node responsible for a key (simple version)."""
        sorted_nodes = sorted(self.node_addresses.keys())

        for node_id in sorted_nodes:
            if node_id >= key_id:
                return node_id

        return sorted_nodes[0]

    def _serialize_value(self, value):
        """Serialize value for transmission."""
        if hasattr(value, 'to_dict'):
            return {'_type': 'Movie', 'data': value.to_dict()}
        return value

    def run_lookup_test(self, keys: List[str], num_tests: int = 10):
        """Run lookup test."""
        logger.info(f"Running {num_tests} lookup tests...")

        test_keys = random.sample(keys, min(num_tests, len(keys)))
        source_nodes = list(self.node_addresses.keys())

        for key in test_keys:
            source = random.choice(source_nodes)
            key_id = hash_key(key, self.m)

            logger.info(f"Lookup '{key}' (id={key_id}) from node {source}")

            # This would trigger routing - for now just log
            # In a full implementation, you'd call a lookup endpoint
            # that triggers the DHT routing protocol

        logger.info("Lookup test complete")

    def run_comprehensive_test(self, items: List[Tuple[str, any]], num_operations: int = 100):
        """
        Run comprehensive performance test collecting hop counts for all operations.
        Returns metrics dictionary for CSV/plotting.
        """
        logger.info(f"Running comprehensive test with {num_operations} operations...")

        results = {
            'lookup': [],
            'insert': [],
            'delete': []
        }

        keys = [key for key, _ in items]
        values_dict = {key: value for key, value in items}
        nodes = list(self.node_addresses.keys())

        # Mix of operations
        operations = ['lookup'] * 50 + ['insert'] * 30 + ['delete'] * 20
        random.shuffle(operations)
        operations = operations[:num_operations]

        for i, op_type in enumerate(operations):
            key = random.choice(keys)
            node = random.choice(nodes)

            try:
                if op_type == 'lookup':
                    hops = self._perform_lookup(node, key)
                    if hops is not None:
                        results['lookup'].append(hops)

                elif op_type == 'insert':
                    value = values_dict.get(key)
                    if value:
                        hops = self._perform_insert(node, key, value)
                        if hops is not None:
                            results['insert'].append(hops)

                elif op_type == 'delete':
                    hops = self._perform_delete(node, key)
                    if hops is not None:
                        results['delete'].append(hops)

            except Exception as e:
                logger.error(f"Operation {op_type} failed: {e}")

            if (i + 1) % 20 == 0:
                logger.info(f"  Progress: {i + 1}/{num_operations}")

        logger.info("Comprehensive test complete")
        return results

    def _perform_lookup(self, node_id: int, key: str) -> int:
        """Perform lookup and return hop count."""
        try:
            url = f"http://{self.node_addresses[node_id]}/lookup"
            response = requests.post(url, json={'key': key}, timeout=self.timeout)
            if response.status_code == 200:
                return response.json().get('hops', 0)
        except:
            pass
        return None

    def _perform_insert(self, node_id: int, key: str, value: any) -> int:
        """Perform insert and return hop count."""
        try:
            url = f"http://{self.node_addresses[node_id]}/insert"
            payload = {
                'key': key,
                'value': self._serialize_value(value)
            }
            response = requests.post(url, json=payload, timeout=self.timeout)
            if response.status_code == 200:
                return response.json().get('hops', 0)
        except:
            pass
        return None

    def _perform_delete(self, node_id: int, key: str) -> int:
        """Perform delete and return hop count."""
        try:
            url = f"http://{self.node_addresses[node_id]}/delete"
            response = requests.post(url, json={'key': key}, timeout=self.timeout)
            if response.status_code == 200:
                return response.json().get('hops', 0)
        except:
            pass
        return None


def main():
    """Main entry point for orchestrator."""
    parser = argparse.ArgumentParser(description='Distributed DHT Orchestrator')

    parser.add_argument('--protocol', choices=['chord', 'pastry'], required=True,
                       help='DHT protocol')
    parser.add_argument('--deployment', choices=['docker', 'k8s', 'local'], default='local',
                       help='Deployment type')
    parser.add_argument('--num-nodes', type=int, default=5,
                       help='Number of nodes (default: 5)')
    parser.add_argument('--num-items', type=int, default=100,
                       help='Number of items to load (default: 100)')
    parser.add_argument('--m', type=int, default=16,
                       help='Bits in identifier space (default: 16)')
    parser.add_argument('--num-operations', type=int, default=100,
                       help='Number of operations to test (default: 100)')
    parser.add_argument('--output', type=str, default=None,
                       help='Output CSV file for results')

    args = parser.parse_args()

    # Discover nodes based on deployment
    if args.deployment == 'docker':
        # Docker Compose: orchestrator runs on host, so use localhost with mapped ports
        # But nodes inside Docker need to use internal network names
        node_addresses = {}  # For orchestrator -> nodes
        internal_addresses = {}  # For node -> node communication
        base_port = 8000 if args.protocol == 'chord' else 9000
        prefix = f"{args.protocol}-node"

        for i in range(args.num_nodes):
            node_id = i * 50  # Spread out IDs
            # External address (orchestrator -> node)
            port = base_port + i
            node_addresses[node_id] = f"localhost:{port}"
            # Internal address (node -> node inside Docker network)
            internal_addresses[node_id] = f"{prefix}-{i}:8000"

    elif args.deployment == 'k8s':
        # Kubernetes: use StatefulSet DNS
        node_addresses = {}
        service_name = f"{args.protocol}-node"
        for i in range(args.num_nodes):
            node_id = i * 50
            pod_name = f"{service_name}-{i}"
            address = f"{pod_name}.{service_name}.dht-system.svc.cluster.local:8000"
            node_addresses[node_id] = address

    else:  # local
        # Local: localhost with different ports
        node_addresses = {}
        base_port = 8000 if args.protocol == 'chord' else 9000
        for i in range(args.num_nodes):
            node_id = i * 50
            address = f"localhost:{base_port + i}"
            node_addresses[node_id] = address

    logger.info(f"Node addresses: {node_addresses}")

    # Create orchestrator with internal addresses if in Docker mode
    if args.deployment == 'docker':
        logger.info(f"Internal addresses (for nodes): {internal_addresses}")
        orchestrator = DistributedOrchestrator(node_addresses, args.protocol, args.m, internal_addresses)
    else:
        orchestrator = DistributedOrchestrator(node_addresses, args.protocol, args.m)

    # Check health
    health = orchestrator.check_health()
    healthy_nodes = sum(1 for v in health.values() if v)
    logger.info(f"Healthy nodes: {healthy_nodes}/{len(health)}")

    if healthy_nodes == 0:
        logger.error("No healthy nodes found. Exiting.")
        return

    # Initialize nodes
    time.sleep(2)  # Wait for nodes to be ready
    orchestrator.initialize_nodes()

    # Load data
    logger.info("Creating sample dataset...")
    items = create_sample_dataset(args.num_items)
    keys = [key for key, _ in items]

    orchestrator.load_data(items)

    # Run comprehensive test
    logger.info(f"Running {args.num_operations} operations...")
    results = orchestrator.run_comprehensive_test(items, num_operations=args.num_operations)

    # Print summary
    logger.info("\n========== RESULTS ==========")
    for op_type, hops_list in results.items():
        if hops_list:
            avg_hops = sum(hops_list) / len(hops_list)
            logger.info(f"{op_type.upper()}: avg={avg_hops:.2f} hops, count={len(hops_list)}")

    # Save to CSV if output specified
    if args.output:
        import csv
        import os
        os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else '.', exist_ok=True)

        with open(args.output, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['protocol', 'operation', 'num_nodes', 'num_items', 'avg_hops', 'max_hops', 'min_hops', 'total_ops'])

            for op_type, hops_list in results.items():
                if hops_list:
                    writer.writerow([
                        args.protocol,
                        op_type,
                        args.num_nodes,
                        args.num_items,
                        sum(hops_list) / len(hops_list),
                        max(hops_list),
                        min(hops_list),
                        len(hops_list)
                    ])

        logger.info(f"Results saved to {args.output}")

    logger.info("Orchestration complete!")


if __name__ == '__main__':
    main()
