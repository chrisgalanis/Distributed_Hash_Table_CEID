import math
from typing import Any, List, Optional, Tuple, Dict, Set
from dht.common import DHT, Message, hash_key
from dht.network import NetworkSimulator
from dht.local_index import LocalStorage


class PastryNode:
    """A node in the Pastry DHT - holds identity and state data only."""

    def __init__(self, node_id: int, m: int, b: int):
        self.node_id = node_id
        self.m = m
        self.b = b
        self.max_id = 2 ** m
        self.base = 2 ** b
        self.num_digits = (m + b - 1) // b

        self.leaf_smaller: List[int] = []
        self.leaf_larger: List[int] = []

        # Routing table: [row][col]
        # Row i = matching prefix of length i
        self.routing_table: List[List[Optional[int]]] = [
            [None] * self.base for _ in range(self.num_digits)
        ]

        self.storage = LocalStorage(use_btree=True)

    @property
    def leaf_set(self) -> List[int]:
        return self.leaf_smaller + self.leaf_larger


class Pastry(DHT):
    """
    Pastry DHT implementation.

    Manages the simulation lifecycle and all Pastry algorithm logic.
    """

    LEAF_HALF = 4  # L/2 nodes on each side of the leaf set

    def __init__(self, m: int = 16, b: int = 4, network=None):
        self.m = m
        self.b = b
        self.max_id = 2 ** m
        self.base = 2 ** b
        self.num_digits = (m + b - 1) // b
        self.network = network or NetworkSimulator()
        self.nodes: Dict[int, PastryNode] = {}

    def _register_node(self, node: PastryNode):
        """Register a node with the network for message handling."""
        self.nodes[node.node_id] = node
        self.network.register_node(
            node.node_id,
            lambda msg, nid=node.node_id: self._handle_message(nid, msg)
        )

    # --- Helpers ---

    def _to_digits(self, node_id: int) -> Tuple[int, ...]:
        """Convert a numeric ID to a tuple of base-2^b digits (MSB first)."""
        result = []
        for i in range(self.num_digits):
            shift = self.m - (i + 1) * self.b
            if shift < 0:
                digit = node_id & ((1 << (self.b + shift)) - 1) if (self.b + shift) > 0 else 0
            else:
                digit = (node_id >> shift) & ((1 << self.b) - 1)
            result.append(digit)
        return tuple(result)

    def _shared_prefix_length(self, id1: int, id2: int) -> int:
        """Return the number of leading digits shared between two IDs."""
        d1 = self._to_digits(id1)
        d2 = self._to_digits(id2)
        length = 0
        for a, b in zip(d1, d2):
            if a == b:
                length += 1
            else:
                break
        return length

    def _get_digit(self, node_id: int, position: int) -> int:
        digits = self._to_digits(node_id)
        if position < len(digits):
            return digits[position]
        return 0

    def _circular_distance(self, a: int, b: int) -> int:
        diff = abs(a - b)
        return min(diff, self.max_id - diff)

    def _circular_between(self, x: int, lo: int, hi: int) -> bool:
        if lo <= hi:
            return lo <= x <= hi
        return x >= lo or x <= hi

    def _find_closest_in(self, key: int, candidates: List[int]) -> Optional[int]:
        if not candidates: return None
        # Tie-break: on equal distance, lower node ID wins
        return min(candidates, key=lambda n: (self._circular_distance(key, n), n))

    # --- Leaf Set Management ---

    def _leaf_set_min(self, node: PastryNode) -> int:
        return node.leaf_smaller[-1] if node.leaf_smaller else node.node_id

    def _leaf_set_max(self, node: PastryNode) -> int:
        return node.leaf_larger[-1] if node.leaf_larger else node.node_id

    def _is_in_leaf_set_range(self, node: PastryNode, key: int) -> bool:
        if not node.leaf_smaller and not node.leaf_larger:
            return True
        return self._circular_between(key, self._leaf_set_min(node), self._leaf_set_max(node))

    def _add_to_leaf_set(self, node: PastryNode, other_id: int):
        if other_id == node.node_id: return
        clockwise = (other_id - node.node_id) % self.max_id
        counter = (node.node_id - other_id) % self.max_id

        if clockwise <= counter:
            if other_id not in node.leaf_larger:
                node.leaf_larger.append(other_id)
                node.leaf_larger.sort(key=lambda x: (x - node.node_id) % self.max_id)
                if len(node.leaf_larger) > self.LEAF_HALF:
                    node.leaf_larger.pop()
        else:
            if other_id not in node.leaf_smaller:
                node.leaf_smaller.append(other_id)
                node.leaf_smaller.sort(key=lambda x: (node.node_id - x) % self.max_id)
                if len(node.leaf_smaller) > self.LEAF_HALF:
                    node.leaf_smaller.pop()

    def _build_leaf_set(self, node: PastryNode, all_nodes: Set[int]):
        """Build leaf set from scratch given all node IDs (for bulk init)."""
        node.leaf_smaller.clear()
        node.leaf_larger.clear()
        for nid in all_nodes:
            if nid != node.node_id:
                self._add_to_leaf_set(node, nid)

    # --- Routing Table Management ---

    def _add_to_routing_table(self, node: PastryNode, other_id: int):
        if other_id == node.node_id: return
        spl = self._shared_prefix_length(node.node_id, other_id)
        if spl >= node.num_digits: return

        col = self._get_digit(other_id, spl)
        if node.routing_table[spl][col] is None:
            node.routing_table[spl][col] = other_id

    def _build_routing_table(self, node: PastryNode, all_nodes: Set[int]):
        """Build routing table from scratch given all node IDs (for bulk init)."""
        node.routing_table = [[None] * node.base for _ in range(node.num_digits)]
        for nid in all_nodes:
            self._add_to_routing_table(node, nid)

    def _get_routing_table_row(self, node: PastryNode, row: int) -> List[Optional[int]]:
        if 0 <= row < len(node.routing_table):
            return list(node.routing_table[row])
        return [None] * node.base

    def _merge_routing_table_row(self, node: PastryNode, row_idx: int, entries: List[Optional[int]]):
        """Merge a row from another node into our table."""
        if row_idx < 0 or row_idx >= node.num_digits: return

        for col, entry in enumerate(entries):
            if entry is not None and entry != node.node_id:
                self._add_to_routing_table(node, entry)

    # --- Core Algorithm: Routing (Slide 13) ---

    def _route(self, node: PastryNode, key: int, visited: Optional[Set[int]] = None) -> int:
        if visited is None: visited = set()
        if node.node_id in visited: return node.node_id
        visited.add(node.node_id)

        # 1. Leaf Set (Exact match or numeric closeness)
        if self._is_in_leaf_set_range(node, key):
            closest = self._find_closest_in(key, node.leaf_set + [node.node_id])
            return closest if closest is not None else node.node_id

        # 2. Routing Table (Long Jump)
        spl = self._shared_prefix_length(node.node_id, key)
        if spl < node.num_digits:
            next_digit = self._get_digit(key, spl)
            entry = node.routing_table[spl][next_digit]
            if entry is not None and entry != node.node_id and entry not in visited:
                return self._forward_route(node, entry, key, visited)

        # 3. Rare Case (The Crawl)
        # ACADEMIC CORRECTION (Slide 13):
        # "Search node T with longest prefix (T,K) out of merged set"
        # Only if prefix lengths are equal do we use numeric distance.
        return self._rare_case_routing(node, key, visited, current_spl=spl)

    def _rare_case_routing(self, node: PastryNode, key: int, visited: Set[int], current_spl: int) -> int:
        best_node = None
        best_spl = current_spl
        best_dist = self._circular_distance(node.node_id, key)

        # Optimization: Generator avoids building a full set of all nodes in memory
        def iterate_known_nodes():
            yield from node.leaf_set
            for row in node.routing_table:
                for entry in row:
                    if entry is not None: yield entry

        for candidate in iterate_known_nodes():
            if candidate == node.node_id or candidate in visited:
                continue

            cand_spl = self._shared_prefix_length(candidate, key)
            cand_dist = self._circular_distance(candidate, key)

            # Slide 13 Logic:
            # 1. Must have prefix at least as long as current node (cand_spl >= current_spl)
            # 2. If longer prefix, it wins immediately.
            # 3. If same prefix, must be numerically closer.
            if cand_spl > best_spl:
                best_spl = cand_spl
                best_dist = cand_dist
                best_node = candidate
            elif cand_spl == best_spl:
                if cand_dist < best_dist:
                    best_dist = cand_dist
                    best_node = candidate

        if best_node:
            return self._forward_route(node, best_node, key, visited)
        return node.node_id

    def _forward_route(self, node: PastryNode, next_hop: int, key: int, visited: Set[int]) -> int:
        msg = Message('route', src_id=node.node_id, dst_id=next_hop,
                      data={'target_id': key, 'visited': visited})
        return self.network.send(msg)

    # --- Core Algorithm: Bootstrapping (Autonomous Join) ---

    def _bootstrap(self, node: PastryNode, bootstrap_node_id: int):
        """
        Perform the full Pastry join protocol for a node.
        """
        if bootstrap_node_id == node.node_id:
            return # First node in network

        # 1. Route JOIN message to ourselves via bootstrap node
        join_msg = Message(
            msg_type='join_route',
            src_id=node.node_id,
            dst_id=bootstrap_node_id,
            data={
                'new_node_id': node.node_id,
                'collected_rows': {},  # Accumulator for routing rows
                'hops_path': [],       # Track path for robustness
            }
        )

        # In a real async network, this would be a callback.
        # In simulation, 'send' returns the final response from Z (closest node).
        result = self.network.send(join_msg)

        if not result: return

        # 2. Process the "Harvest" (Slide 19-24)
        # Populate routing table from collected rows
        collected_rows = result.get('collected_rows', {})
        for row_idx, entries in collected_rows.items():
            self._merge_routing_table_row(node, row_idx, entries)

        # Populate leaf set from Z (the closest node)
        z_leaves = result.get('leaf_set', ([], []))
        all_candidates = set(z_leaves[0] + z_leaves[1] + result.get('hops_path', []))
        all_candidates.add(result.get('z_node'))

        for cand in all_candidates:
            if cand: self._add_to_leaf_set(node, cand)
            if cand: self._add_to_routing_table(node, cand)

        # 3. Notify everyone in our new state
        self._broadcast_arrival(node)

        # 4. Request keys from Z and all leaf neighbors
        donors = set(node.leaf_set)
        z_node = result.get('z_node')
        if z_node: donors.add(z_node)
        for donor_id in donors:
            self._request_keys_from(node, donor_id)

    def _broadcast_arrival(self, node: PastryNode):
        """Send 'notify_arrival' to all neighbors."""
        targets = set(node.leaf_set)
        for row in node.routing_table:
            for entry in row:
                if entry: targets.add(entry)

        for target in targets:
            self.network.send(Message(
                'notify_arrival', src_id=node.node_id, dst_id=target,
                data={'new_node_id': node.node_id}
            ), count_hop=False)

    def _request_keys_from(self, node: PastryNode, z_node_id: int):
        """Ask Z for keys that now belong to me, and delete them from Z."""
        if z_node_id is None: return
        msg = Message('transfer_keys', src_id=node.node_id, dst_id=z_node_id)
        items = self.network.send(msg, count_hop=False)

        if items:
            keys_to_take = []
            for k, v_list in items:
                key_id = hash_key(k, self.m)
                my_dist = self._circular_distance(key_id, node.node_id)
                z_dist = self._circular_distance(key_id, z_node_id)
                if my_dist < z_dist or (my_dist == z_dist and node.node_id < z_node_id):
                    for v in v_list:
                        node.storage.put(k, v)
                    keys_to_take.append(k)
            # Tell Z to delete the transferred keys
            for k in keys_to_take:
                self.network.send(Message('delete', src_id=node.node_id, dst_id=z_node_id, key=k), count_hop=False)

    # --- Message Handling ---

    def _handle_message(self, node_id: int, msg: Message) -> Any:
        """Handle incoming messages for a specific node."""
        node = self.nodes[node_id]
        if msg.msg_type == 'route':
            return self._handle_route_msg(node, msg)
        elif msg.msg_type == 'lookup':
            return node.storage.get(msg.key)
        elif msg.msg_type == 'insert':
            return node.storage.put(msg.key, msg.value)
        elif msg.msg_type == 'delete':
            return node.storage.delete(msg.key)
        elif msg.msg_type == 'update':
            return node.storage.update(msg.key, msg.value)
        elif msg.msg_type == 'get_all_keys':
            return node.storage.get_all_keys()
        elif msg.msg_type == 'get_all_items':
            return node.storage.get_all_items()
        elif msg.msg_type == 'join_route':
            return self._handle_join_route_msg(node, msg)
        elif msg.msg_type == 'notify_arrival':
            return self._handle_notify_arrival(node, msg)
        elif msg.msg_type == 'transfer_keys':
            return node.storage.get_all_items()
        return None

    def _handle_route_msg(self, node: PastryNode, msg: Message) -> Any:
        return self._route(node, msg.data['target_id'], msg.data.get('visited'))

    def _handle_notify_arrival(self, node: PastryNode, msg: Message) -> bool:
        new_id = msg.data['new_node_id']
        self._add_to_leaf_set(node, new_id)
        self._add_to_routing_table(node, new_id)
        return True

    def _handle_join_route_msg(self, node: PastryNode, msg: Message) -> Dict:
        """
        Handle a JOIN message passing through.
        Logic: Add MY routing row to the message, then forward or finish.
        """
        new_id = msg.data['new_node_id']
        collected_rows = msg.data.get('collected_rows', {})
        hops_path = msg.data.get('hops_path', [])

        # ACADEMIC NOTE (Slide 19): "Each node sends row in routing table to X"
        # We contribute the row corresponding to the shared prefix length.
        spl = self._shared_prefix_length(node.node_id, new_id)
        if spl not in collected_rows:
            collected_rows[spl] = self._get_routing_table_row(node, spl)

        hops_path.append(node.node_id)

        # Check if we are the destination (closest node)
        if self._is_in_leaf_set_range(node, new_id):
            closest = self._find_closest_in(new_id, node.leaf_set + [node.node_id])

            if closest == node.node_id or closest is None or closest in hops_path:
                return {
                    'collected_rows': collected_rows,
                    'leaf_set': (list(node.leaf_smaller), list(node.leaf_larger)),
                    'z_node': node.node_id,
                    'hops_path': hops_path,
                }

            return self._forward_join(closest, msg, collected_rows, hops_path)

        # Standard Routing Table forwarding
        if spl < node.num_digits:
            next_digit = self._get_digit(new_id, spl)
            entry = node.routing_table[spl][next_digit]
            if entry is not None and entry != node.node_id and entry not in hops_path:
                return self._forward_join(entry, msg, collected_rows, hops_path)

        # Rare case fallback (not implemented for join for brevity, rare in stable nets)
        return { # Fallback: Assume I am Z
            'collected_rows': collected_rows,
            'leaf_set': (list(node.leaf_smaller), list(node.leaf_larger)),
            'z_node': node.node_id,
            'hops_path': hops_path,
        }

    def _forward_join(self, next_hop, original_msg, collected, path):
        """Helper to forward the modified join message."""
        new_msg = Message(
            'join_route', src_id=original_msg.src_id, dst_id=next_hop,
            data={
                'new_node_id': original_msg.data['new_node_id'],
                'collected_rows': collected,
                'hops_path': path,
            }
        )
        return self.network.send(new_msg)

    # --- Public DHT API ---

    def build(self, node_ids: List[int], items: List[Tuple[str, Any]]):
        """Bulk-build the network with full knowledge (bootstrapping)."""
        if not node_ids: raise ValueError("Need nodes")

        normalized_ids = set(nid % self.max_id for nid in node_ids)

        for nid in normalized_ids:
            node = PastryNode(nid, self.m, self.b)
            self._register_node(node)

        for node in self.nodes.values():
            self._build_leaf_set(node, normalized_ids)
            self._build_routing_table(node, normalized_ids)

        for k, v in items:
            self.insert(k, v)

    def join(self, new_node_id: int) -> int:
        """Add a node via the Pastry bootstrap protocol."""
        new_node_id %= self.max_id
        if new_node_id in self.nodes: return 0

        # Create the node
        new_node = PastryNode(new_node_id, self.m, self.b)
        self._register_node(new_node)

        # Bootstrap using any existing node
        if len(self.nodes) > 1:
            # Pick a random existing node (not self)
            bootstrap_id = next(nid for nid in self.nodes if nid != new_node_id)
            self.network.reset_counters()
            self._bootstrap(new_node, bootstrap_id)
            return self.network.get_stats()['total_hops']
        return 0

    def _dht_op(self, key: str, op: str, value: Any = None, source_node: Optional[int] = None) -> Any:
        """Generic helper for CRUD operations."""
        if not self.nodes: return None
        self.network.reset_counters()

        if source_node is None:
            source_node = next(iter(self.nodes))

        node = self.nodes[source_node]
        key_id = hash_key(key, self.m)

        # Ask source node to route to key owner
        responsible_id = self._route(node, key_id)

        # Send actual operation to responsible node
        msg = Message(op, src_id=source_node, dst_id=responsible_id, key=key, value=value)
        res = self.network.send(msg, count_hop=False)

        # For lookups, return result + hops. For others, just hops.
        hops = self.network.get_stats()['total_hops']
        return (res, hops) if op == 'lookup' else hops

    def lookup(self, key: str, source_node: Optional[int] = None) -> Tuple[Optional[Any], int]:
        return self._dht_op(key, 'lookup', source_node=source_node)

    def insert(self, key: str, value: Any, source_node: Optional[int] = None) -> int:
        return self._dht_op(key, 'insert', value, source_node=source_node)

    def delete(self, key: str, source_node: Optional[int] = None) -> int:
        return self._dht_op(key, 'delete', source_node=source_node)

    def update(self, key: str, value: Any, source_node: Optional[int] = None) -> int:
        return self._dht_op(key, 'update', value, source_node=source_node)

    def leave(self, node_id: int, graceful: bool = True) -> int:
        node_id %= self.max_id
        if node_id not in self.nodes:
            return 0

        self.network.reset_counters()
        departing = self.nodes[node_id]

        if graceful:
            # Transfer each key to the node that will be responsible after departure
            for key_str, values in departing.storage.get_all_items():
                key_id = hash_key(key_str, self.m)
                # Find closest remaining node to this key
                best_node = None
                best_dist = self.max_id
                for nid in departing.leaf_set:
                    if nid in self.nodes and nid != node_id:
                        d = self._circular_distance(key_id, nid)
                        if d < best_dist or (d == best_dist and (best_node is None or nid < best_node)):
                            best_dist = d
                            best_node = nid
                if best_node and best_node in self.nodes:
                    for v in values:
                        self.nodes[best_node].storage.put(key_str, v)

        self.network.unregister_node(node_id)
        del self.nodes[node_id]

        # Remove departed node from all remaining nodes' state
        for nid, node in self.nodes.items():
            if node_id in node.leaf_smaller:
                node.leaf_smaller.remove(node_id)
            if node_id in node.leaf_larger:
                node.leaf_larger.remove(node_id)
            for row in range(len(node.routing_table)):
                for col in range(len(node.routing_table[row])):
                    if node.routing_table[row][col] == node_id:
                        node.routing_table[row][col] = None

        return self.network.get_stats()['total_hops']

    def get_all_nodes(self) -> List[int]:
        return list(self.nodes.keys())
