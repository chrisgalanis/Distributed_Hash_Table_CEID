"""Chord DHT implementation."""

import math
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple, Dict
from dht.common import DHT, Message, hash_key, distance_clockwise
from dht.network import NetworkSimulator
from dht.local_index import LocalStorage


@dataclass
class FingerEntry:
    #entry of a nodes finger table | 
    # finger[k].start = (n + 2^(k-1)) mod 2^m
    # finger[k].node = successor(finger[k].start)
    start: int  # The ID this finger is responsible for finding
    node: Optional[int] = None  # The successor of start


class ChordNode:
    """A node in the Chord DHT ring - holds identity and state data only."""

    def __init__(self, node_id: int, m: int):
        self.node_id = node_id
        self.m = m  # Number of bits in identifier space
        self.max_id = 2 ** m

        # Chord routing state
        self.successor: Optional[int] = None
        self.predecessor: Optional[int] = None

        # Initialize finger table with FingerEntry objects
        # finger[k].start = (n + 2^k) mod 2^m for k in [0, m-1]
        self.finger_table: List[FingerEntry] = []
        for k in range(m):
            start = (node_id + 2 ** k) % self.max_id
            self.finger_table.append(FingerEntry(start=start, node=None))

        # Local storage
        self.storage = LocalStorage(use_btree=True)


class Chord(DHT):
    """Chord DHT implementation."""

    def __init__(self, m: int = 16, network=None):
        """
        Initialize Chord DHT.
        m: number of bits in identifier space (default 16 -> max 65536 nodes)
        network: optional network layer (defaults to NetworkSimulator)
        """
        self.m = m
        self.max_id = 2 ** m
        self.network = network or NetworkSimulator()
        self.nodes: Dict[int, ChordNode] = {}

    def _register_node(self, node: ChordNode):
        """Register a node with the network for message handling."""
        self.nodes[node.node_id] = node
        # Only register handler for NetworkSimulator, not DistributedNetwork
        # NetworkSimulator has 'nodes' attribute (dict of handlers)
        if hasattr(self.network, 'nodes'):
            self.network.register_node(
                node.node_id,
                lambda msg, nid=node.node_id: self._handle_message(nid, msg)
            )

    def _handle_message(self, node_id: int, msg: Message) -> Any:
        """Handle incoming messages for a specific node."""
        node = self.nodes[node_id]
        if msg.msg_type == 'find_successor':
            target_id = msg.data['target_id']
            return self._find_successor_for_node(node, target_id)
        elif msg.msg_type == 'get_predecessor':
            return node.predecessor
        elif msg.msg_type == 'get_successor':
            return node.successor
        elif msg.msg_type == 'notify':
            # Stabilization: potential predecessor is notifying us to update them
            potential_pred = msg.data.get('node_id')
            self._notify(node, potential_pred)
            return True
        elif msg.msg_type == 'lookup':
            return node.storage.get(msg.key)
        elif msg.msg_type == 'insert':
            node.storage.put(msg.key, msg.value)
            return True
        elif msg.msg_type == 'delete':
            node.storage.delete(msg.key)
            return True
        elif msg.msg_type == 'update':
            node.storage.update(msg.key, msg.value)
            return True
        elif msg.msg_type == 'get_all_keys':
            return node.storage.get_all_keys()
        elif msg.msg_type == 'get_all_items':
            return node.storage.get_all_items()
        elif msg.msg_type == 'transfer_keys':
            # Transfer keys in a range to another node
            start = msg.data.get('start')
            end = msg.data.get('end')
            return self._transfer_keys(node, start, end)
        else:
            return None

    def _find_successor_for_node(self, node: ChordNode, target_id: int) -> int:
        """Find successor of target_id from a node's perspective."""
        # If target is between us and our successor, return successor
        if self._in_range(target_id, node.node_id, node.successor, inclusive_end=True):
            return node.successor

        # Otherwise, forward to closest preceding node
        closest = self._closest_preceding_node(node, target_id)
        if closest == node.node_id:
            return node.successor

        # Forward request
        msg = Message(
            msg_type='find_successor',
            src_id=node.node_id,
            dst_id=closest,
            data={'target_id': target_id}
        )
        return self.network.send(msg)

    def _closest_preceding_node(self, node: ChordNode, target_id: int) -> int:
        """Find closest node preceding target_id in the node's finger table."""
        # Check finger table in reverse order (largest jumps first)
        for i in range(node.m - 1, -1, -1):
            finger_node = node.finger_table[i].node
            if finger_node is not None and self._in_range(finger_node, node.node_id, target_id, inclusive_start=False, inclusive_end=False):
                return finger_node

        return node.node_id

    @staticmethod
    def _in_range(val: int, start: int, end: int,
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

    def _transfer_keys(self, node: ChordNode, start: int, end: int) -> List[Tuple[str, List[Any]]]:
        """Transfer keys in range (start, end] from a node."""
        items_to_transfer = []
        keys_to_remove = []

        for key in node.storage.get_all_keys():
            key_id = hash_key(key, node.m)
            if self._in_range(key_id, start, end, inclusive_end=True):
                values = node.storage.get(key)
                items_to_transfer.append((key, values))
                keys_to_remove.append(key)

        # Remove transferred keys
        for key in keys_to_remove:
            node.storage.delete(key)

        return items_to_transfer

    #in theory its called periodically to verify our successor and notify him
    def stabilize(self, node_id: int) -> bool:
        """Run stabilization for a specific node."""
        # ask our successor for his predecessor (x)
        #   If x is between us and our current successor, we should make x our new successor
        #   Then we must notify our new successor about us
        node = self.nodes[node_id]
        if node.successor is None:
            return False

        # Get predecessor of our successor
        msg = Message(
            msg_type='get_predecessor',
            src_id=node.node_id,
            dst_id=node.successor
        )
        x = self.network.send(msg, count_hop=False)

        updated = False
        # If x exists and is in interval (self, successor), update successor
        if x is not None and x != node.node_id and x != node.successor:
            if self._in_range(x, node.node_id, node.successor,
                              inclusive_start=False, inclusive_end=False):
                node.successor = x
                # Update first finger table entry to match
                node.finger_table[0].node = x
                updated = True

        # Notify our successor about us (we might be its predecessor)
        msg = Message(
            msg_type='notify',
            src_id=node.node_id,
            dst_id=node.successor,
            data={'node_id': node.node_id}
        )
        self.network.send(msg, count_hop=False)

        return updated

    #called when a node thinks it might be our predecessor
    def _notify(self, node: ChordNode, potential_predecessor: int):
        """Handle notification that a node might be our predecessor."""
        #If a node thinks he is our new predecessor we:
        # 1. IF we already have one
        # 2. IF he is between our current predecessor and us, then we MUST update him as our new predecessor
        if potential_predecessor is None:
            return

        if node.predecessor is None:
            node.predecessor = potential_predecessor
        elif self._in_range(potential_predecessor, node.predecessor, node.node_id,
                            inclusive_start=False, inclusive_end=False):
            node.predecessor = potential_predecessor

    def fix_finger(self, node_id: int, i: int) -> bool:
        """Fix finger table entry i for a specific node."""
        node = self.nodes[node_id]
        if i < 0 or i >= node.m:
            return False

        finger_entry = node.finger_table[i]
        old_node = finger_entry.node

        # Find successor of finger[i].start
        msg = Message(
            msg_type='find_successor',
            src_id=node.node_id,
            dst_id=node.node_id,
            data={'target_id': finger_entry.start}
        )
        new_node = self.network.send(msg, count_hop=False)
        finger_entry.node = new_node

        # Keep successor in sync with finger[0]
        if i == 0:
            node.successor = new_node

        return old_node != new_node

    def build(self, node_ids: List[int], items: List[Tuple[str, Any]]):
        """Build the Chord ring with given nodes and items."""
        if not node_ids:
            raise ValueError("Must provide at least one node")

        # Create nodes
        for nid in node_ids:
            node = ChordNode(nid % self.max_id, self.m)
            self._register_node(node)

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
                # finger_table[i].start is already set in ChordNode.__init__
                # Just need to set the node (successor of start)
                finger = self._find_successor_static(node.finger_table[i].start, sorted_nodes)
                node.finger_table[i].node = finger

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
        new_node = ChordNode(new_node_id, self.m)

        if not self.nodes:
            # First node
            new_node.successor = new_node_id
            new_node.predecessor = new_node_id
            self._register_node(new_node)
            return 0

        # Pick an existing node before registering the new one
        arbitrary_node = list(self.nodes.keys())[0]

        # Register new node so it can receive messages during routing
        self._register_node(new_node)

        # Find successor of new node
        successor = self._find_successor(new_node_id, arbitrary_node)

        # Get predecessor of successor - this is a bit off-paper implementation, usually this is handled by the stabilization but it just made more sense (as seen from sioutas lecture) to copy the predecessor from new node's successor.
        msg = Message(msg_type='get_predecessor', src_id=new_node_id, dst_id=successor)
        predecessor = self.network.send(msg, count_hop=False)

        # Set new node's pointers
        new_node.successor = successor
        new_node.predecessor = predecessor

        # Update predecessor's successor
        self.nodes[predecessor].successor = new_node_id

        # Update successor's predecessor
        self.nodes[successor].predecessor = new_node_id

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
                # finger_table[i].start is already correct
                finger = self._find_successor_static(node.finger_table[i].start, sorted_nodes)
                node.finger_table[i].node = finger

    def stabilize_all(self, rounds: int = 3):
        # TODO: Should run in the background - could happen by spawning a thread that runs multiple rounds of stabilize on nodes that were updated, or just run stabilize for random nodes every [interval]
        #runs multiple rounds of stabilize and fix_finger
        for _ in range(rounds):
            # Run stabilize on all nodes
            for node_id in self.nodes:
                self.stabilize(node_id)

        # Fix all finger table entries
        for node_id in self.nodes:
            for i in range(self.m):
                self.fix_finger(node_id, i)

    def get_all_nodes(self) -> List[int]:
        """Get list of all node IDs."""
        return list(self.nodes.keys())
