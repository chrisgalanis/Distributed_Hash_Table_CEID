"""Common interfaces and utilities for DHT implementations."""

import hashlib
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Message:
    """Message passed between DHT nodes."""
    msg_type: str
    src_id: int
    dst_id: int
    key: Optional[str] = None
    value: Optional[Any] = None
    data: Optional[Dict] = None


class DHT(ABC):
    """Abstract base class for DHT implementations."""

    @abstractmethod
    def build(self, node_ids: List[int], items: List[Tuple[str, Any]]):
        """Build the DHT with given nodes and initial items."""
        pass

    @abstractmethod
    def lookup(self, key: str, source_node: Optional[int] = None) -> Tuple[Optional[Any], int]:
        """
        Lookup a key in the DHT.
        Returns: (value, hops)
        """
        pass

    @abstractmethod
    def insert(self, key: str, value: Any, source_node: Optional[int] = None) -> int:
        """
        Insert a key-value pair.
        Returns: hops
        """
        pass

    @abstractmethod
    def delete(self, key: str, source_node: Optional[int] = None) -> int:
        """
        Delete a key.
        Returns: hops
        """
        pass

    @abstractmethod
    def update(self, key: str, value: Any, source_node: Optional[int] = None) -> int:
        """
        Update a key's value.
        Returns: hops
        """
        pass

    @abstractmethod
    def join(self, new_node_id: int) -> int:
        """
        Add a new node to the DHT.
        Returns: hops
        """
        pass

    @abstractmethod
    def leave(self, node_id: int, graceful: bool = True) -> int:
        """
        Remove a node from the DHT.
        Returns: hops
        """
        pass

    @abstractmethod
    def get_all_nodes(self) -> List[int]:
        """Get list of all node IDs."""
        pass


def hash_key(key: str, bits: int = 160) -> int:
    """
    Hash a key to an integer in the range [0, 2^bits).
    Uses SHA-1 for consistency.
    """
    hash_bytes = hashlib.sha1(key.encode('utf-8')).digest()
    hash_int = int.from_bytes(hash_bytes, byteorder='big')
    return hash_int % (2 ** bits)


def normalize_title(title: str) -> str:
    """Normalize movie title for consistent key generation."""
    return title.strip().lower()


def distance_clockwise(start: int, end: int, max_val: int) -> int:
    """Calculate clockwise distance in circular space."""
    if end >= start:
        return end - start
    else:
        return max_val - start + end
