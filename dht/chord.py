"""Chord DHT implementation."""

import math
from typing import Any, List, Optional, Tuple, Dict
from dht.common import DHT, Message, hash_key, distance_clockwise
from dht.network import NetworkSimulator
from dht.local_index import LocalStorage


class ChordNode:
    """A node in the Chord DHT ring."""

    def __init__(self, node_id: int, m: int, network: NetworkSimulator):
        self.node_id = node_id
        self.m = m  # Number of bits in identifier space
        self.max_id = 2 ** m
        self.network = network

        # Chord routing state
        self.successor: Optional[int] = None
        self.predecessor: Optional[int] = None
        self.finger_table: List[Optional[int]] = [None] * m

        # Local storage
        self.storage = LocalStorage(use_btree=True)

        # Register with network
        network.register_node(node_id, self.handle_message)

    def handle_message(self, msg: Message) -> Any:
        """Handle incoming messages."""
        if msg.msg_type == 'find_successor':
            target_id = msg.data['target_id']
            return self._find_successor_handler(target_id)
        elif msg.msg_type == 'get_predecessor':
            return self.predecessor
        elif msg.msg_type == 'get_successor':
            return self.successor
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
        elif msg.msg_type == 'transfer_keys':
            # Transfer keys in a range to another node
            start = msg.data.get('start')
            end = msg.data.get('end')
            return self._transfer_keys(start, end)
        else:
            return None

    def _find_successor_handler(self, target_id: int) -> int:
        """Find successor of target_id."""
        # If target is between us and our successor, return successor
        if self._in_range(target_id, self.node_id, self.successor, inclusive_end=True):
            return self.successor

        # Otherwise, forward to closest preceding node
        closest = self._closest_preceding_node(target_id)
        if closest == self.node_id:
            return self.successor

        # Forward request
        msg = Message(
            msg_type='find_successor',
            src_id=self.node_id,
            dst_id=closest,
            data={'target_id': target_id}
        )
        return self.network.send(msg)

    def _closest_preceding_node(self, target_id: int) -> int:
        """Find closest node preceding target_id."""
        # Check finger table in reverse order
        for i in range(self.m - 1, -1, -1):
            finger = self.finger_table[i]
            if finger and self._in_range(finger, self.node_id, target_id, inclusive_start=False, inclusive_end=False):
                return finger

        return self.node_id

    def _in_range(self, val: int, start: int, end: int,
                  inclusive_start: bool = False, inclusive_end: bool = False) -> bool:
        """Check if val is in the circular range (start, end)."""
        if start == end:
            return inclusive_start or inclusive_end

        if start < end:
            if inclusive_start and inclusive_end:
                return start <= val <= end
            elif inclusive_start:
                return start <= val < end
            elif inclusive_end:
                return start < val <= end
            else:
                return start < val < end
        else:  # Wraps around
            if inclusive_start and inclusive_end:
                return val >= start or val <= end
            elif inclusive_start:
                return val >= start or val < end
            elif inclusive_end:
                return val > start or val <= end
            else:
                return val > start or val < end

    def _transfer_keys(self, start: int, end: int) -> List[Tuple[str, List[Any]]]:
        """Transfer keys in range (start, end] to another node."""
        items_to_transfer = []
        keys_to_remove = []

        for key in self.storage.get_all_keys():
            key_id = hash_key(key, self.m)
            if self._in_range(key_id, start, end, inclusive_end=True):
                values = self.storage.get(key)
                items_to_transfer.append((key, values))
                keys_to_remove.append(key)

        # Remove transferred keys
        for key in keys_to_remove:
            self.storage.delete(key)

        return items_to_transfer


class Chord(DHT):
    """Chord DHT implementation."""

    def __init__(self, m: int = 16):
        """
        Initialize Chord DHT.
        m: number of bits in identifier space (default 16 -> max 65536 nodes)
        """
        self.m = m
        self.max_id = 2 ** m
        self.network = NetworkSimulator()
        self.nodes: Dict[int, ChordNode] = {}

    def build(self, node_ids: List[int], items: List[Tuple[str, Any]]):
        """Build the Chord ring with given nodes and items."""
        if not node_ids:
            raise ValueError("Must provide at least one node")

        # Create nodes
        for nid in node_ids:
            node = ChordNode(nid % self.max_id, self.m, self.network)
            self.nodes[nid % self.max_id] = node

        # Sort nodes by ID
        sorted_nodes = sorted(self.nodes.keys())
        n = len(sorted_nodes)

        # Set successor and predecessor for each node
        for i, nid in enumerate(sorted_nodes):
            node = self.nodes[nid]
            node.successor = sorted_nodes[(i + 1) % n]
            node.predecessor = sorted_nodes[(i - 1) % n]

        # Build finger tables
        for nid in sorted_nodes:
            node = self.nodes[nid]
            for i in range(self.m):
                start = (nid + 2 ** i) % self.max_id
                # Find successor of start
                finger = self._find_successor_static(start, sorted_nodes)
                node.finger_table[i] = finger

        # Insert initial items
        for key, value in items:
            self.insert(key, value)

    def _find_successor_static(self, target_id: int, sorted_nodes: List[int]) -> int:
        """Find successor during static build (without message passing)."""
        for nid in sorted_nodes:
            if nid >= target_id:
                return nid
        return sorted_nodes[0]  # Wrap around

    def lookup(self, key: str, source_node: Optional[int] = None) -> Tuple[Optional[Any], int]:
        """Lookup key in Chord ring."""
        if not self.nodes:
            return None, 0

        self.network.reset_counters()

        # Determine source node
        if source_node is None:
            source_node = list(self.nodes.keys())[0]

        # Find responsible node
        key_id = hash_key(key, self.m)
        responsible_node = self._find_successor(key_id, source_node)

        # Lookup value at responsible node
        msg = Message(
            msg_type='lookup',
            src_id=source_node,
            dst_id=responsible_node,
            key=key
        )
        values = self.network.send(msg, count_hop=False)  # Don't count final lookup

        stats = self.network.get_stats()
        return values, stats['total_hops']

    def insert(self, key: str, value: Any, source_node: Optional[int] = None) -> int:
        """Insert key-value pair into Chord ring."""
        if not self.nodes:
            return 0

        self.network.reset_counters()

        if source_node is None:
            source_node = list(self.nodes.keys())[0]

        key_id = hash_key(key, self.m)
        responsible_node = self._find_successor(key_id, source_node)

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
        """Delete key from Chord ring."""
        if not self.nodes:
            return 0

        self.network.reset_counters()

        if source_node is None:
            source_node = list(self.nodes.keys())[0]

        key_id = hash_key(key, self.m)
        responsible_node = self._find_successor(key_id, source_node)

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
        """Update key's value in Chord ring."""
        if not self.nodes:
            return 0

        self.network.reset_counters()

        if source_node is None:
            source_node = list(self.nodes.keys())[0]

        key_id = hash_key(key, self.m)
        responsible_node = self._find_successor(key_id, source_node)

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

    def _find_successor(self, target_id: int, source_node: int) -> int:
        """Find successor of target_id starting from source_node."""
        msg = Message(
            msg_type='find_successor',
            src_id=source_node,
            dst_id=source_node,
            data={'target_id': target_id}
        )
        return self.network.send(msg)

    def join(self, new_node_id: int) -> int:
        """Add new node to Chord ring."""
        new_node_id = new_node_id % self.max_id

        if new_node_id in self.nodes:
            return 0  # Node already exists

        self.network.reset_counters()

        # Create new node
        new_node = ChordNode(new_node_id, self.m, self.network)

        if not self.nodes:
            # First node
            new_node.successor = new_node_id
            new_node.predecessor = new_node_id
            self.nodes[new_node_id] = new_node
            return 0

        # Find successor of new node
        arbitrary_node = list(self.nodes.keys())[0]
        successor = self._find_successor(new_node_id, arbitrary_node)

        # Get predecessor of successor
        msg = Message(msg_type='get_predecessor', src_id=new_node_id, dst_id=successor)
        predecessor = self.network.send(msg, count_hop=False)

        # Set new node's pointers
        new_node.successor = successor
        new_node.predecessor = predecessor

        # Update predecessor's successor
        self.nodes[predecessor].successor = new_node_id

        # Update successor's predecessor
        self.nodes[successor].predecessor = new_node_id

        # Add node to network
        self.nodes[new_node_id] = new_node

        # Rebuild finger tables for simplicity
        self._rebuild_fingers()

        # Transfer keys from successor
        msg = Message(
            msg_type='transfer_keys',
            src_id=new_node_id,
            dst_id=successor,
            data={'start': predecessor, 'end': new_node_id}
        )
        transferred_items = self.network.send(msg, count_hop=False)

        # Store transferred items
        for key, values in transferred_items:
            for value in values:
                new_node.storage.put(key, value)

        stats = self.network.get_stats()
        return stats['total_hops']

    def leave(self, node_id: int, graceful: bool = True) -> int:
        """Remove node from Chord ring."""
        node_id = node_id % self.max_id

        if node_id not in self.nodes:
            return 0

        self.network.reset_counters()
        node = self.nodes[node_id]

        if graceful:
            # Transfer all keys to successor
            all_items = node.storage.get_all_items()
            successor_node = self.nodes[node.successor]
            for key, values in all_items:
                for value in values:
                    successor_node.storage.put(key, value)

        # Update predecessor's successor
        if node.predecessor in self.nodes:
            self.nodes[node.predecessor].successor = node.successor

        # Update successor's predecessor
        if node.successor in self.nodes:
            self.nodes[node.successor].predecessor = node.predecessor

        # Remove node
        self.network.unregister_node(node_id)
        del self.nodes[node_id]

        # Rebuild finger tables
        if self.nodes:
            self._rebuild_fingers()

        stats = self.network.get_stats()
        return stats['total_hops']

    def _rebuild_fingers(self):
        """Rebuild finger tables for all nodes."""
        sorted_nodes = sorted(self.nodes.keys())

        for nid in sorted_nodes:
            node = self.nodes[nid]
            for i in range(self.m):
                start = (nid + 2 ** i) % self.max_id
                finger = self._find_successor_static(start, sorted_nodes)
                node.finger_table[i] = finger

    def get_all_nodes(self) -> List[int]:
        """Get list of all node IDs."""
        return list(self.nodes.keys())
