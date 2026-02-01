"""Workload generator for DHT experiments."""

import random
from typing import List, Tuple, Dict, Any
from enum import Enum


class OperationType(Enum):
    """Types of DHT operations."""
    LOOKUP = "lookup"
    INSERT = "insert"
    DELETE = "delete"
    UPDATE = "update"
    JOIN = "join"
    LEAVE = "leave"


class Operation:
    """Represents a single DHT operation."""

    def __init__(self, op_type: OperationType, key: str = None, value: Any = None, node_id: int = None):
        self.op_type = op_type
        self.key = key
        self.value = value
        self.node_id = node_id

    def __repr__(self):
        if self.op_type in [OperationType.JOIN, OperationType.LEAVE]:
            return f"Operation({self.op_type.value}, node_id={self.node_id})"
        else:
            return f"Operation({self.op_type.value}, key={self.key})"


class WorkloadGenerator:
    """Generates workload for DHT testing."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)

    def generate_mixed_workload(
        self,
        num_operations: int,
        keys: List[str],
        operation_mix: Dict[OperationType, float] = None
    ) -> List[Operation]:
        """
        Generate a mixed workload of operations.

        Args:
            num_operations: Number of operations to generate
            keys: Pool of keys to use
            operation_mix: Dictionary mapping operation type to probability
                          Default: 40% lookup, 20% insert, 10% delete, 10% update, 10% join, 10% leave

        Returns:
            List of Operation objects
        """
        if operation_mix is None:
            operation_mix = {
                OperationType.LOOKUP: 0.4,
                OperationType.INSERT: 0.2,
                OperationType.DELETE: 0.1,
                OperationType.UPDATE: 0.1,
                OperationType.JOIN: 0.1,
                OperationType.LEAVE: 0.1
            }

        # Normalize probabilities
        total = sum(operation_mix.values())
        normalized_mix = {k: v / total for k, v in operation_mix.items()}

        operations = []
        inserted_keys = set()
        next_node_id = 10000

        for _ in range(num_operations):
            # Choose operation type
            rand = random.random()
            cumulative = 0
            op_type = OperationType.LOOKUP

            for ot, prob in normalized_mix.items():
                cumulative += prob
                if rand <= cumulative:
                    op_type = ot
                    break

            # Generate operation
            if op_type == OperationType.LOOKUP:
                key = random.choice(keys)
                operations.append(Operation(op_type, key=key))

            elif op_type == OperationType.INSERT:
                key = random.choice(keys)
                value = f"value_{random.randint(1, 10000)}"
                inserted_keys.add(key)
                operations.append(Operation(op_type, key=key, value=value))

            elif op_type == OperationType.DELETE:
                if inserted_keys:
                    key = random.choice(list(inserted_keys))
                    inserted_keys.discard(key)
                else:
                    key = random.choice(keys)
                operations.append(Operation(op_type, key=key))

            elif op_type == OperationType.UPDATE:
                key = random.choice(keys)
                value = f"updated_value_{random.randint(1, 10000)}"
                operations.append(Operation(op_type, key=key, value=value))

            elif op_type == OperationType.JOIN:
                node_id = next_node_id
                next_node_id += 1
                operations.append(Operation(op_type, node_id=node_id))

            elif op_type == OperationType.LEAVE:
                # For leave, we'd need to track active nodes
                # For now, use a dummy node ID
                node_id = random.randint(0, 1000)
                operations.append(Operation(op_type, node_id=node_id))

        return operations

    def generate_lookup_workload(self, num_lookups: int, keys: List[str]) -> List[Operation]:
        """Generate workload of only lookup operations."""
        operations = []
        for _ in range(num_lookups):
            key = random.choice(keys)
            operations.append(Operation(OperationType.LOOKUP, key=key))
        return operations

    def generate_insert_workload(self, items: List[Tuple[str, Any]]) -> List[Operation]:
        """Generate workload of insert operations for all items."""
        operations = []
        for key, value in items:
            operations.append(Operation(OperationType.INSERT, key=key, value=value))
        return operations

    def generate_node_churn_workload(
        self,
        num_joins: int,
        num_leaves: int,
        existing_nodes: List[int]
    ) -> List[Operation]:
        """Generate workload simulating node churn (joins and leaves)."""
        operations = []
        next_node_id = max(existing_nodes) + 1 if existing_nodes else 1000

        # Interleave joins and leaves
        for i in range(max(num_joins, num_leaves)):
            if i < num_joins:
                operations.append(Operation(OperationType.JOIN, node_id=next_node_id))
                next_node_id += 1

            if i < num_leaves and existing_nodes:
                node_to_remove = random.choice(existing_nodes)
                existing_nodes.remove(node_to_remove)
                operations.append(Operation(OperationType.LEAVE, node_id=node_to_remove))

        return operations
