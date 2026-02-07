"""HTTP REST API server for a single DHT node."""

from flask import Flask, request, jsonify
import argparse
import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dht.chord import ChordNode, FingerEntry
from dht.pastry import PastryNode
from dht.common import Message
from distributed.network_real import DistributedNetwork

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DHTNodeServer:
    """HTTP server wrapping a DHT node."""

    def __init__(self, node_id: int, protocol: str, m: int, b: int = 4):
        """
        Initialize DHT node server.

        Args:
            node_id: Unique node identifier
            protocol: "chord" or "pastry"
            m: Number of bits in identifier space
            b: Pastry parameter (bits per digit)
        """
        self.node_id = node_id
        self.protocol = protocol
        self.m = m
        self.b = b

        # Create network
        self.network = DistributedNetwork()

        # Create DHT node
        if protocol == "chord":
            self.node = ChordNode(node_id, m, self.network)
        elif protocol == "pastry":
            # For Pastry, we need all nodes to build routing structures
            # This will be initialized later via /init endpoint
            self.node = None
        else:
            raise ValueError(f"Unknown protocol: {protocol}")

        self.app = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint."""
            return jsonify({'status': 'ok', 'node_id': self.node_id})

        @self.app.route('/message', methods=['POST'])
        def handle_message():
            """Handle incoming DHT messages."""
            try:
                data = request.get_json()

                # Reconstruct message
                msg = Message(
                    msg_type=data['msg_type'],
                    src_id=data['src_id'],
                    dst_id=data['dst_id'],
                    key=data.get('key'),
                    value=self._deserialize_value(data.get('value')),
                    data=data.get('data')
                )

                # Handle message
                if self.node is None:
                    return jsonify({'error': 'Node not initialized'}), 500

                result = self.node.handle_message(msg)

                # Serialize result
                return jsonify({'result': self._serialize_value(result)})

            except Exception as e:
                logger.error(f"Error handling message: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/init', methods=['POST'])
        def initialize():
            """
            Initialize node with routing information.
            For Chord: set successor, predecessor, finger table
            For Pastry: build routing structures with all nodes
            """
            try:
                data = request.get_json()

                if self.protocol == "chord":
                    # Set Chord routing info
                    self.node.successor = data.get('successor')
                    self.node.predecessor = data.get('predecessor')

                    # Convert finger table from list of node IDs to list of FingerEntry objects
                    finger_nodes = data.get('finger_table', [None] * self.m)
                    finger_table = []
                    for k in range(self.m):
                        start = (self.node_id + 2 ** k) % (2 ** self.m)
                        node = finger_nodes[k] if k < len(finger_nodes) else None
                        finger_table.append(FingerEntry(start=start, node=node))
                    self.node.finger_table = finger_table

                elif self.protocol == "pastry":
                    # Initialize Pastry node with all nodes
                    all_nodes = set(data.get('all_nodes', []))
                    self.node = PastryNode(self.node_id, self.m, self.b,
                                          self.network, all_nodes)

                # Register other nodes in network
                node_registry = data.get('node_registry', {})
                for nid_str, address in node_registry.items():
                    self.network.register_node(int(nid_str), address)

                return jsonify({'status': 'initialized'})

            except Exception as e:
                logger.error(f"Error initializing node: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/store', methods=['POST'])
        def store():
            """Store a key-value pair locally."""
            try:
                data = request.get_json()
                key = data['key']
                value = self._deserialize_value(data['value'])

                self.node.storage.put(key, value)

                return jsonify({'status': 'stored'})

            except Exception as e:
                logger.error(f"Error storing data: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/info', methods=['GET'])
        def info():
            """Get node information."""
            try:
                info_data = {
                    'node_id': self.node_id,
                    'protocol': self.protocol,
                    'm': self.m
                }

                if self.protocol == "chord":
                    info_data['successor'] = self.node.successor
                    info_data['predecessor'] = self.node.predecessor
                    info_data['finger_table'] = self.node.finger_table

                elif self.protocol == "pastry":
                    info_data['leaf_set'] = self.node.leaf_set if self.node else []

                return jsonify(info_data)

            except Exception as e:
                logger.error(f"Error getting info: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/stats', methods=['GET'])
        def stats():
            """Get network statistics (hop counts)."""
            try:
                return jsonify(self.network.get_stats())
            except Exception as e:
                logger.error(f"Error getting stats: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/reset_stats', methods=['POST'])
        def reset_stats():
            """Reset network statistics."""
            try:
                self.network.reset_counters()
                return jsonify({'status': 'reset'})
            except Exception as e:
                logger.error(f"Error resetting stats: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/lookup', methods=['POST'])
        def lookup():
            """Perform DHT lookup operation."""
            try:
                data = request.get_json()
                key = data['key']

                if self.node is None:
                    return jsonify({'error': 'Node not initialized'}), 500

                # Perform lookup (node handles routing and hop counting)
                values, hops = self.node.lookup(key)

                return jsonify({
                    'values': self._serialize_value(values),
                    'hops': hops
                })

            except Exception as e:
                logger.error(f"Error in lookup: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/insert', methods=['POST'])
        def insert():
            """Perform DHT insert operation."""
            try:
                data = request.get_json()
                key = data['key']
                value = self._deserialize_value(data['value'])

                if self.node is None:
                    return jsonify({'error': 'Node not initialized'}), 500

                # Perform insert (node handles routing and hop counting)
                hops = self.node.insert(key, value)

                return jsonify({
                    'hops': hops,
                    'status': 'inserted'
                })

            except Exception as e:
                logger.error(f"Error in insert: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

        @self.app.route('/delete', methods=['POST'])
        def delete():
            """Perform DHT delete operation."""
            try:
                data = request.get_json()
                key = data['key']

                if self.node is None:
                    return jsonify({'error': 'Node not initialized'}), 500

                # Perform delete (node handles routing and hop counting)
                hops = self.node.delete(key)

                return jsonify({
                    'hops': hops,
                    'status': 'deleted'
                })

            except Exception as e:
                logger.error(f"Error in delete: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500

    def _serialize_value(self, value):
        """Serialize value for JSON response."""
        if value is None:
            return None

        if hasattr(value, 'to_dict'):
            return {'_type': 'Movie', 'data': value.to_dict()}

        if isinstance(value, list):
            return [self._serialize_value(v) for v in value]

        return value

    def _deserialize_value(self, value):
        """Deserialize value from JSON."""
        if value is None:
            return None

        if isinstance(value, dict) and value.get('_type') == 'Movie':
            from dht.data_loader import Movie
            return Movie(value['data'])

        if isinstance(value, list):
            return [self._deserialize_value(v) for v in value]

        return value

    def run(self, host: str = '0.0.0.0', port: int = 8000):
        """Run the Flask server."""
        logger.info(f"Starting {self.protocol.upper()} node {self.node_id} on {host}:{port}")
        self.app.run(host=host, port=port, threaded=True)


def main():
    """Main entry point for node server."""
    parser = argparse.ArgumentParser(description='DHT Node Server')

    parser.add_argument('--node-id', type=int, required=True,
                       help='Node ID')
    parser.add_argument('--protocol', choices=['chord', 'pastry'], required=True,
                       help='DHT protocol')
    parser.add_argument('--port', type=int, default=8000,
                       help='Port to listen on (default: 8000)')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--m', type=int, default=16,
                       help='Number of bits in identifier space (default: 16)')
    parser.add_argument('--b', type=int, default=4,
                       help='Pastry b parameter (default: 4)')

    args = parser.parse_args()

    # Create and run server
    server = DHTNodeServer(args.node_id, args.protocol, args.m, args.b)
    server.run(host=args.host, port=args.port)


if __name__ == '__main__':
    main()
