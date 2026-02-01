"""Network simulator with hop counting."""

from typing import Dict, Callable, Any, Optional
from threading import Lock
from dht.common import Message


class NetworkSimulator:
    """
    Simulates a network that routes messages between nodes.
    Tracks hop counts for performance measurement.
    """

    def __init__(self):
        self.nodes: Dict[int, Callable] = {}
        self.lock = Lock()
        self.total_hops = 0
        self.message_count = 0

    def register_node(self, node_id: int, handler: Callable[[Message], Any]):
        """Register a node's message handler."""
        with self.lock:
            self.nodes[node_id] = handler

    def unregister_node(self, node_id: int):
        """Remove a node from the network."""
        with self.lock:
            if node_id in self.nodes:
                del self.nodes[node_id]

    def send(self, msg: Message, count_hop: bool = True) -> Any:
        """
        Send a message to a node and return the response.
        If count_hop is True, increments hop counter.
        """
        with self.lock:
            if msg.dst_id not in self.nodes:
                raise ValueError(f"Node {msg.dst_id} not in network")

            handler = self.nodes[msg.dst_id]
            if count_hop:
                self.total_hops += 1
                self.message_count += 1

        # Call handler outside of lock to avoid deadlock
        return handler(msg)

    def reset_counters(self):
        """Reset hop and message counters."""
        with self.lock:
            self.total_hops = 0
            self.message_count = 0

    def get_stats(self) -> Dict[str, int]:
        """Get current network statistics."""
        with self.lock:
            return {
                'total_hops': self.total_hops,
                'message_count': self.message_count,
                'avg_hops': self.total_hops / self.message_count if self.message_count > 0 else 0
            }
