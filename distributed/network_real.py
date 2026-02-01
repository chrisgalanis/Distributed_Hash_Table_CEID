"""Real network implementation using HTTP/REST for distributed deployment."""

import requests
import json
from typing import Dict, Callable, Any, Optional
from threading import Lock
from dht.common import Message
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DistributedNetwork:
    """
    Real network that uses HTTP to communicate between nodes.
    Replaces NetworkSimulator for distributed deployment.
    """

    def __init__(self, node_registry: Optional[Dict[int, str]] = None):
        """
        Initialize distributed network.

        Args:
            node_registry: Dict mapping node_id -> "host:port" address
        """
        self.node_registry: Dict[int, str] = node_registry or {}
        self.lock = Lock()
        self.total_hops = 0
        self.message_count = 0
        self.timeout = 5  # seconds

    def register_node(self, node_id: int, address: str):
        """
        Register a node's network address.

        Args:
            node_id: Node identifier
            address: "host:port" string
        """
        with self.lock:
            self.node_registry[node_id] = address
            logger.info(f"Registered node {node_id} at {address}")

    def unregister_node(self, node_id: int):
        """Remove a node from the registry."""
        with self.lock:
            if node_id in self.node_registry:
                del self.node_registry[node_id]
                logger.info(f"Unregistered node {node_id}")

    def send(self, msg: Message, count_hop: bool = True) -> Any:
        """
        Send a message to a remote node via HTTP.

        Args:
            msg: Message to send
            count_hop: Whether to count this as a hop

        Returns:
            Response from the remote node
        """
        with self.lock:
            if msg.dst_id not in self.node_registry:
                raise ValueError(f"Node {msg.dst_id} not in registry")

            address = self.node_registry[msg.dst_id]

            if count_hop:
                self.total_hops += 1
                self.message_count += 1

        # Prepare HTTP request
        url = f"http://{address}/message"

        # Serialize message
        payload = {
            'msg_type': msg.msg_type,
            'src_id': msg.src_id,
            'dst_id': msg.dst_id,
            'key': msg.key,
            'value': self._serialize_value(msg.value),
            'data': msg.data
        }

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()

            result = response.json()
            return self._deserialize_value(result.get('result'))

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send message to node {msg.dst_id} at {address}: {e}")
            raise

    def _serialize_value(self, value: Any) -> Any:
        """Serialize value for JSON transmission."""
        if value is None:
            return None

        # Handle Movie objects
        if hasattr(value, 'to_dict'):
            return {'_type': 'Movie', 'data': value.to_dict()}

        # Handle lists
        if isinstance(value, list):
            return [self._serialize_value(v) for v in value]

        return value

    def _deserialize_value(self, value: Any) -> Any:
        """Deserialize value from JSON."""
        if value is None:
            return None

        # Handle Movie objects
        if isinstance(value, dict) and value.get('_type') == 'Movie':
            from dht.data_loader import Movie
            return Movie(value['data'])

        # Handle lists
        if isinstance(value, list):
            return [self._deserialize_value(v) for v in value]

        return value

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

    def get_all_nodes(self) -> list[int]:
        """Get all registered node IDs."""
        with self.lock:
            return list(self.node_registry.keys())


class NodeDiscovery:
    """
    Node discovery for Kubernetes environments.
    Uses Kubernetes service DNS for finding nodes.
    """

    @staticmethod
    def discover_nodes_k8s(service_name: str, namespace: str = "default",
                           start_port: int = 8000, count: int = 10) -> Dict[int, str]:
        """
        Discover DHT nodes in Kubernetes using DNS.

        Args:
            service_name: K8s service name (e.g., "dht-node")
            namespace: K8s namespace
            start_port: Starting port number
            count: Expected number of nodes

        Returns:
            Dict mapping node_id -> address
        """
        nodes = {}

        # In k8s, stateful set pods are named: {service_name}-{ordinal}
        # They resolve to: {service_name}-{ordinal}.{service_name}.{namespace}.svc.cluster.local
        for i in range(count):
            node_id = i
            pod_name = f"{service_name}-{i}"
            # K8s headless service DNS
            address = f"{pod_name}.{service_name}.{namespace}.svc.cluster.local:{start_port}"
            nodes[node_id] = address

        return nodes

    @staticmethod
    def discover_nodes_docker(service_name: str, count: int = 10,
                            start_port: int = 8000) -> Dict[int, str]:
        """
        Discover DHT nodes in Docker Compose.

        Args:
            service_name: Docker service name
            count: Expected number of nodes
            start_port: Starting port number

        Returns:
            Dict mapping node_id -> address
        """
        nodes = {}

        # In docker-compose, services can be scaled and accessed by index
        for i in range(count):
            node_id = i
            # Docker internal DNS resolves service names
            address = f"{service_name}:{start_port + i}"
            nodes[node_id] = address

        return nodes

    @staticmethod
    def discover_nodes_local(count: int = 10, start_port: int = 8000) -> Dict[int, str]:
        """
        Discover DHT nodes running locally on different ports.

        Args:
            count: Number of nodes
            start_port: Starting port number

        Returns:
            Dict mapping node_id -> address
        """
        nodes = {}

        for i in range(count):
            node_id = i
            address = f"localhost:{start_port + i}"
            nodes[node_id] = address

        return nodes
