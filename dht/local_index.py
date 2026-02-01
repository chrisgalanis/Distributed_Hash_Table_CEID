"""B+ Tree implementation for local indexing at each peer."""

from typing import Any, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class BPlusTreeNode:
    """Node in a B+ tree."""
    is_leaf: bool = True
    keys: List[str] = field(default_factory=list)
    children: List['BPlusTreeNode'] = field(default_factory=list)
    values: List[List[Any]] = field(default_factory=list)  # Only for leaf nodes
    next_leaf: Optional['BPlusTreeNode'] = None  # Link to next leaf for range queries
    parent: Optional['BPlusTreeNode'] = None


class BPlusTree:
    """
    B+ Tree index for string keys.
    Supports exact-match queries and stores multiple values per key.
    """

    def __init__(self, order: int = 4):
        """
        Initialize B+ tree with given order.
        Order = maximum number of children per internal node.
        """
        self.order = order
        self.root = BPlusTreeNode(is_leaf=True)
        self.min_keys = (order + 1) // 2 - 1

    def search(self, key: str) -> List[Any]:
        """Search for a key and return all associated values."""
        node = self._find_leaf(key)
        if key in node.keys:
            idx = node.keys.index(key)
            return node.values[idx]
        return []

    def insert(self, key: str, value: Any):
        """Insert a key-value pair. Supports multiple values per key."""
        leaf = self._find_leaf(key)

        # If key exists, append to values list
        if key in leaf.keys:
            idx = leaf.keys.index(key)
            leaf.values[idx].append(value)
            return

        # Insert new key
        idx = self._find_insert_position(leaf.keys, key)
        leaf.keys.insert(idx, key)
        leaf.values.insert(idx, [value])

        # Split if necessary
        if len(leaf.keys) >= self.order:
            self._split_leaf(leaf)

    def delete(self, key: str, value: Optional[Any] = None):
        """
        Delete a key or a specific value associated with the key.
        If value is None, delete all values for the key.
        """
        leaf = self._find_leaf(key)
        if key not in leaf.keys:
            return

        idx = leaf.keys.index(key)

        if value is None:
            # Delete entire key
            leaf.keys.pop(idx)
            leaf.values.pop(idx)
        else:
            # Delete specific value
            if value in leaf.values[idx]:
                leaf.values[idx].remove(value)
                # If no values left, remove the key
                if not leaf.values[idx]:
                    leaf.keys.pop(idx)
                    leaf.values.pop(idx)

    def update(self, key: str, new_values: List[Any]):
        """Update all values for a key."""
        leaf = self._find_leaf(key)
        if key in leaf.keys:
            idx = leaf.keys.index(key)
            leaf.values[idx] = new_values
        else:
            # Key doesn't exist, insert it
            for val in new_values:
                self.insert(key, val)

    def _find_leaf(self, key: str) -> BPlusTreeNode:
        """Find the leaf node where key should be."""
        node = self.root
        while not node.is_leaf:
            idx = self._find_child_index(node.keys, key)
            node = node.children[idx]
        return node

    def _find_child_index(self, keys: List[str], key: str) -> int:
        """Find which child to descend to."""
        for i, k in enumerate(keys):
            if key < k:
                return i
        return len(keys)

    def _find_insert_position(self, keys: List[str], key: str) -> int:
        """Find position to insert key in sorted list."""
        for i, k in enumerate(keys):
            if key < k:
                return i
        return len(keys)

    def _split_leaf(self, leaf: BPlusTreeNode):
        """Split a leaf node that has too many keys."""
        mid = len(leaf.keys) // 2

        # Create new leaf with right half
        new_leaf = BPlusTreeNode(is_leaf=True)
        new_leaf.keys = leaf.keys[mid:]
        new_leaf.values = leaf.values[mid:]
        new_leaf.next_leaf = leaf.next_leaf
        new_leaf.parent = leaf.parent

        # Update original leaf
        leaf.keys = leaf.keys[:mid]
        leaf.values = leaf.values[:mid]
        leaf.next_leaf = new_leaf

        # Promote middle key to parent
        promote_key = new_leaf.keys[0]
        self._insert_in_parent(leaf, promote_key, new_leaf)

    def _split_internal(self, node: BPlusTreeNode):
        """Split an internal node that has too many keys."""
        mid = len(node.keys) // 2
        promote_key = node.keys[mid]

        # Create new internal node with right half
        new_node = BPlusTreeNode(is_leaf=False)
        new_node.keys = node.keys[mid + 1:]
        new_node.children = node.children[mid + 1:]
        new_node.parent = node.parent

        # Update children's parent pointers
        for child in new_node.children:
            child.parent = new_node

        # Update original node
        node.keys = node.keys[:mid]
        node.children = node.children[:mid + 1]

        # Promote key to parent
        self._insert_in_parent(node, promote_key, new_node)

    def _insert_in_parent(self, left: BPlusTreeNode, key: str, right: BPlusTreeNode):
        """Insert key and right node into parent."""
        if left.parent is None:
            # Create new root
            new_root = BPlusTreeNode(is_leaf=False)
            new_root.keys = [key]
            new_root.children = [left, right]
            left.parent = new_root
            right.parent = new_root
            self.root = new_root
            return

        parent = left.parent
        idx = self._find_insert_position(parent.keys, key)
        parent.keys.insert(idx, key)
        parent.children.insert(idx + 1, right)

        # Split parent if necessary
        if len(parent.keys) >= self.order:
            self._split_internal(parent)

    def get_all_keys(self) -> List[str]:
        """Get all keys in sorted order."""
        keys = []
        node = self.root
        # Find leftmost leaf
        while not node.is_leaf:
            node = node.children[0]
        # Traverse leaf nodes
        while node:
            keys.extend(node.keys)
            node = node.next_leaf
        return keys


class LocalStorage:
    """
    Local storage for a DHT node.
    Uses both dictionary (for fast exact match) and B+ tree (for demonstration).
    """

    def __init__(self, use_btree: bool = True):
        self.data: dict[str, List[Any]] = {}
        self.use_btree = use_btree
        if use_btree:
            self.btree = BPlusTree(order=4)

    def get(self, key: str) -> List[Any]:
        """Get all values for a key."""
        if self.use_btree:
            return self.btree.search(key)
        return self.data.get(key, [])

    def put(self, key: str, value: Any):
        """Store a value for a key."""
        if key not in self.data:
            self.data[key] = []
        self.data[key].append(value)

        if self.use_btree:
            self.btree.insert(key, value)

    def delete(self, key: str):
        """Delete all values for a key."""
        if key in self.data:
            del self.data[key]

        if self.use_btree:
            self.btree.delete(key)

    def update(self, key: str, values: List[Any]):
        """Update all values for a key."""
        self.data[key] = values

        if self.use_btree:
            self.btree.update(key, values)

    def get_all_keys(self) -> List[str]:
        """Get all stored keys."""
        return list(self.data.keys())

    def get_all_items(self) -> List[Tuple[str, List[Any]]]:
        """Get all key-value pairs."""
        return [(k, v) for k, v in self.data.items()]
