"""Pastry DHT implementation."""

import math
from typing import Any, List, Optional, Tuple, Dict, Set
from dht.common import DHT, Message, hash_key
from dht.network import NetworkSimulator
from dht.local_index import LocalStorage


class PastryNode:
    """A node in the Pastry DHT."""

    def __init__(self, node_id: int, m: int, b: int, network: NetworkSimulator, all_nodes: Set[int]):
        self.node_id = node_id
        self.m = m  # Number of bits in identifier
        self.b = b  # Number of bits per digit (typically 4 for hex)
        self.max_id = 2 ** m
        self.base = 2 ** b  # Base for routing (16 for b=4)
        self.network = network

        # Pastry routing state
        self.leaf_set: List[int] = []  # Closest nodes numerically
        self.routing_table: List[List[Optional[int]]] = []  # Prefix-based routing

        # Local storage
        self.storage = LocalStorage(use_btree=True)

        # Initialize routing structures
        self._init_routing_table()

        # Build routing structures
        self._build_routing_structures(all_nodes)

        # Register with network (only for NetworkSimulator, not DistributedNetwork)
        if hasattr(network, 'nodes'):
            network.register_node(node_id, self.handle_message)

    def _init_routing_table(self):
        """Initialize empty routing table."""
        rows = (self.m + self.b - 1) // self.b  # Number of rows
        self.routing_table = [[None] * self.base for _ in range(rows)]

    def _build_routing_structures(self, all_nodes: Set[int]):
        """Build leaf set and routing table from all nodes."""
        # Build leaf set (L closest nodes on each side)
        L = 8  # Typical leaf set size
        nodes_list = sorted(all_nodes)

        # Find position of this node
        idx = nodes_list.index(self.node_id)
        n = len(nodes_list)

        # Get L/2 nodes on each side (wrapping around)
        leaf_size = min(L, n - 1)
        self.leaf_set = []
        for i in range(1, leaf_size + 1):
            left_idx = (idx - i) % n
            right_idx = (idx + i) % n
            if len(self.leaf_set) < leaf_size:
                self.leaf_set.append(nodes_list[left_idx])
            if len(self.leaf_set) < leaf_size:
                self.leaf_set.append(nodes_list[right_idx])

        # Build routing table
        for node in all_nodes:
            if node == self.node_id:
                continue

            shared_prefix_len = self._shared_prefix_length(self.node_id, node)
            if shared_prefix_len < len(self.routing_table):
                digit = self._get_digit(node, shared_prefix_len)
                if self.routing_table[shared_prefix_len][digit] is None:
                    self.routing_table[shared_prefix_len][digit] = node

    def _shared_prefix_length(self, id1: int, id2: int) -> int:
        """Calculate length of shared prefix in base-2^b."""
        s1 = self._to_base_b_string(id1)
        s2 = self._to_base_b_string(id2)

        shared = 0
        for c1, c2 in zip(s1, s2):
            if c1 == c2:
                shared += 1
            else:
                break
        return shared

    def _to_base_b_string(self, node_id: int) -> str:
        """Convert node ID to base-2^b string."""
        digits = (self.m + self.b - 1) // self.b
        result = []
        for i in range(digits):
            digit = (node_id >> (self.m - (i + 1) * self.b)) & ((1 << self.b) - 1)
            result.append(digit)
        return tuple(result)

    def _get_digit(self, node_id: int, position: int) -> int:
        """Get digit at position in base-2^b representation."""
        digits_tuple = self._to_base_b_string(node_id)
        if position < len(digits_tuple):
            return digits_tuple[position]
        return 0

    def handle_message(self, msg: Message) -> Any:
        """Handle incoming messages."""
        if msg.msg_type == 'route':
            target_id = msg.data['target_id']
            visited = msg.data.get('visited', None)
            return self._route_handler(target_id, visited)
        elif msg.msg_type == 'lookup':
            return self.storage.get(msg.key)
        elif msg.msg_type == 'insert':
            self.storage.put(msg.key, msg.value)
            return True
        elif msg.msg_type == 'delete':
            self.storage.delete(msg.key)
            return True
        elif msg.msg_type == 'update':
            self.storage.update(msg.key, msg.value)
            return True
        elif msg.msg_type == 'get_all_keys':
            return self.storage.get_all_keys()
        elif msg.msg_type == 'get_all_items':
            return self.storage.get_all_items()
        elif msg.msg_type == 'get_leaf_set':
            return self.leaf_set
        elif msg.msg_type == 'transfer_keys':
            return self._get_responsible_keys()
        else:
            return None

    def route(self, target_id: int) -> int:
        """
        Public method to route to node responsible for target_id.
        Initiates routing through the DHT.
        """
        return self._route_handler(target_id)

    def _route_handler(self, target_id: int, visited: Set[int] = None) -> int:
        """Route to node responsible for target_id."""
        # Initialize visited set to detect loops
        if visited is None:
            visited = set()

        # Loop detection
        if self.node_id in visited:
            return self.node_id
        visited.add(self.node_id)

        # Check if target is in leaf set range or we're the closest
        if self._is_in_leaf_set_range(target_id):
            # Find closest node in leaf set
            return self._find_closest_node(target_id, self.leaf_set + [self.node_id])

        # Use routing table
        shared_len = self._shared_prefix_length(self.node_id, target_id)
        next_digit = self._get_digit(target_id, shared_len)

        if shared_len < len(self.routing_table) and self.routing_table[shared_len][next_digit] is not None:
            next_hop = self.routing_table[shared_len][next_digit]

            # Don't forward to ourselves or already visited nodes
            if next_hop == self.node_id or next_hop in visited:
                return self.node_id

            # Forward to next hop
            msg = Message(
                msg_type='route',
                src_id=self.node_id,
                dst_id=next_hop,
                data={'target_id': target_id, 'visited': visited}
            )
            return self.network.send(msg)

        # Rare case: forward to numerically closer node
        candidates = [n for row in self.routing_table for n in row if n is not None]
        candidates.extend(self.leaf_set)

        # Filter out visited nodes
        candidates = [c for c in candidates if c not in visited]

        if not candidates:
            # No more candidates, we must be responsible
            return self.node_id

        candidates.append(self.node_id)
        closest = self._find_closest_node(target_id, candidates)

        if closest == self.node_id:
            return self.node_id

        msg = Message(
            msg_type='route',
            src_id=self.node_id,
            dst_id=closest,
            data={'target_id': target_id, 'visited': visited}
        )
        return self.network.send(msg)

    def _is_in_leaf_set_range(self, target_id: int) -> bool:
        """Check if target is within leaf set range."""
        if not self.leaf_set:
            return True

        min_leaf = min(self.leaf_set + [self.node_id])
        max_leaf = max(self.leaf_set + [self.node_id])

        # Simple check (doesn't handle wrap-around perfectly)
        return min_leaf <= target_id <= max_leaf

    def _find_closest_node(self, target_id: int, candidates: List[int]) -> int:
        """Find numerically closest node to target."""
        if not candidates:
            return self.node_id

        closest = candidates[0]
        min_dist = self._circular_distance(target_id, closest)

        for node in candidates[1:]:
            dist = self._circular_distance(target_id, node)
            if dist < min_dist:
                min_dist = dist
                closest = node

        return closest

    def _circular_distance(self, id1: int, id2: int) -> int:
        """Calculate circular distance between two IDs."""
        direct = abs(id1 - id2)
        wrap = self.max_id - direct
        return min(direct, wrap)

    def _get_responsible_keys(self) -> List[Tuple[str, List[Any]]]:
        """Get all keys this node is responsible for."""
        return self.storage.get_all_items()

    # High-level DHT operations (for both simulated and distributed modes)
    def lookup(self, key: str) -> Tuple[Optional[List[Any]], int]:
        """
        Lookup a key in the DHT.
        Returns (values, hops) tuple.
        """
        if hasattr(self.network, 'reset_counters'):
            self.network.reset_counters()

        key_id = hash_key(key, self.m)
        responsible_node = self.route(key_id)

        msg = Message(
            msg_type='lookup',
            src_id=self.node_id,
            dst_id=responsible_node,
            key=key
        )
        values = self.network.send(msg, count_hop=False)

        if hasattr(self.network, 'get_stats'):
            stats = self.network.get_stats()
            hops = stats['total_hops']
        else:
            hops = 0

        return values, hops

    def insert(self, key: str, value: Any) -> int:
        """Insert a key-value pair into the DHT. Returns number of hops."""
        if hasattr(self.network, 'reset_counters'):
            self.network.reset_counters()

        key_id = hash_key(key, self.m)
        responsible_node = self.route(key_id)

        msg = Message(
            msg_type='insert',
            src_id=self.node_id,
            dst_id=responsible_node,
            key=key,
            value=value
        )
        self.network.send(msg, count_hop=False)

        if hasattr(self.network, 'get_stats'):
            return self.network.get_stats()['total_hops']
        return 0

    def delete(self, key: str) -> int:
        """Delete a key from the DHT. Returns number of hops."""
        if hasattr(self.network, 'reset_counters'):
            self.network.reset_counters()

        key_id = hash_key(key, self.m)
        responsible_node = self.route(key_id)

        msg = Message(
            msg_type='delete',
            src_id=self.node_id,
            dst_id=responsible_node,
            key=key
        )
        self.network.send(msg, count_hop=False)

        if hasattr(self.network, 'get_stats'):
            return self.network.get_stats()['total_hops']
        return 0

    def update(self, key: str, value: Any) -> int:
        """Update a key's value in the DHT. Returns number of hops."""
        if hasattr(self.network, 'reset_counters'):
            self.network.reset_counters()

        key_id = hash_key(key, self.m)
        responsible_node = self.route(key_id)

        msg = Message(
            msg_type='update',
            src_id=self.node_id,
            dst_id=responsible_node,
            key=key,
            value=value
        )
        self.network.send(msg, count_hop=False)

        if hasattr(self.network, 'get_stats'):
            return self.network.get_stats()['total_hops']
        return 0


class Pastry(DHT):
    """Pastry DHT implementation."""

    def __init__(self, m: int = 16, b: int = 4):
        """
        Initialize Pastry DHT.
        m: number of bits in identifier space (default 16)
        b: number of bits per digit (default 4 for base-16)
        """
        self.m = m
        self.b = b
        self.max_id = 2 ** m
        self.network = NetworkSimulator()
        self.nodes: Dict[int, PastryNode] = {}

    def build(self, node_ids: List[int], items: List[Tuple[str, Any]]):
        """Build Pastry network with given nodes and items."""
        if not node_ids:
            raise ValueError("Must provide at least one node")

        # Normalize node IDs
        normalized_ids = set(nid % self.max_id for nid in node_ids)

        # Create all nodes
        for nid in normalized_ids:
            node = PastryNode(nid, self.m, self.b, self.network, normalized_ids)
            self.nodes[nid] = node

        # Insert initial items
        for key, value in items:
            self.insert(key, value)

    def lookup(self, key: str, source_node: Optional[int] = None) -> Tuple[Optional[Any], int]:
        """Lookup key in Pastry network."""
        if not self.nodes:
            return None, 0

        self.network.reset_counters()

        if source_node is None:
            source_node = list(self.nodes.keys())[0]

        # Route to responsible node
        key_id = hash_key(key, self.m)
        responsible_node = self._route(key_id, source_node)

        # Lookup value
        msg = Message(
            msg_type='lookup',
            src_id=source_node,
            dst_id=responsible_node,
            key=key
        )
        values = self.network.send(msg, count_hop=False)

        stats = self.network.get_stats()
        return values, stats['total_hops']

    def insert(self, key: str, value: Any, source_node: Optional[int] = None) -> int:
        """Insert key-value pair into Pastry network."""
        if not self.nodes:
            return 0

        self.network.reset_counters()

        if source_node is None:
            source_node = list(self.nodes.keys())[0]

        key_id = hash_key(key, self.m)
        responsible_node = self._route(key_id, source_node)

        msg = Message(
            msg_type='insert',
            src_id=source_node,
            dst_id=responsible_node,
            key=key,
            value=value
        )
        self.network.send(msg, count_hop=False)

        stats = self.network.get_stats()
        return stats['total_hops']

    def delete(self, key: str, source_node: Optional[int] = None) -> int:
        """Delete key from Pastry network."""
        if not self.nodes:
            return 0

        self.network.reset_counters()

        if source_node is None:
            source_node = list(self.nodes.keys())[0]

        key_id = hash_key(key, self.m)
        responsible_node = self._route(key_id, source_node)

        msg = Message(
            msg_type='delete',
            src_id=source_node,
            dst_id=responsible_node,
            key=key
        )
        self.network.send(msg, count_hop=False)

        stats = self.network.get_stats()
        return stats['total_hops']

    def update(self, key: str, value: Any, source_node: Optional[int] = None) -> int:
        """Update key's value in Pastry network."""
        if not self.nodes:
            return 0

        self.network.reset_counters()

        if source_node is None:
            source_node = list(self.nodes.keys())[0]

        key_id = hash_key(key, self.m)
        responsible_node = self._route(key_id, source_node)

        msg = Message(
            msg_type='update',
            src_id=source_node,
            dst_id=responsible_node,
            key=key,
            value=value
        )
        self.network.send(msg, count_hop=False)

        stats = self.network.get_stats()
        return stats['total_hops']

    def _route(self, target_id: int, source_node: int) -> int:
        """Route from source to node responsible for target_id."""
        msg = Message(
            msg_type='route',
            src_id=source_node,
            dst_id=source_node,
            data={'target_id': target_id}
        )
        return self.network.send(msg)

    def join(self, new_node_id: int) -> int:
        """Add new node to Pastry network."""
        new_node_id = new_node_id % self.max_id

        if new_node_id in self.nodes:
            return 0

        self.network.reset_counters()

        # Get current node IDs
        all_node_ids = set(self.nodes.keys())
        all_node_ids.add(new_node_id)

        # Create new node
        new_node = PastryNode(new_node_id, self.m, self.b, self.network, all_node_ids)
        self.nodes[new_node_id] = new_node

        # Rebuild routing structures for all nodes (simplified approach)
        for nid in self.nodes:
            self.nodes[nid]._build_routing_structures(all_node_ids)

        # Transfer keys to new node if needed
        # (In a full implementation, we'd transfer keys from nearby nodes)

        stats = self.network.get_stats()
        return stats['total_hops']

    def leave(self, node_id: int, graceful: bool = True) -> int:
        """Remove node from Pastry network."""
        node_id = node_id % self.max_id

        if node_id not in self.nodes:
            return 0

        self.network.reset_counters()
        node = self.nodes[node_id]

        if graceful:
            # Transfer all keys to closest node in leaf set
            all_items = node.storage.get_all_items()
            if node.leaf_set:
                closest = node.leaf_set[0]
                successor_node = self.nodes[closest]
                for key, values in all_items:
                    for value in values:
                        successor_node.storage.put(key, value)

        # Remove node
        self.network.unregister_node(node_id)
        del self.nodes[node_id]

        # Rebuild routing structures
        if self.nodes:
            all_node_ids = set(self.nodes.keys())
            for nid in self.nodes:
                self.nodes[nid]._build_routing_structures(all_node_ids)

        stats = self.network.get_stats()
        return stats['total_hops']

    def get_all_nodes(self) -> List[int]:
        """Get list of all node IDs."""
        return list(self.nodes.keys())
