"""
UDP BitTorrent tracker protocol parser
Based on BEP 15: http://wiki.theory.org/BitTorrentSpecification#UDP_Tracker_Protocol
"""
import struct
import time
from typing import Dict, Tuple, Optional
from .common import (
    CONNECTION_ID, ACTIONS, EVENTS, to_uint32, bin_to_hex, hex_to_bin,
    DEFAULT_ANNOUNCE_PEERS, MAX_ANNOUNCE_PEERS, UDP_CONNECTION_TIMEOUT
)


class UDPConnection:
    """Manages UDP connection state"""

    def __init__(self, remote_addr: Tuple[str, int]):
        self.remote_addr = remote_addr
        self.connection_id: Optional[int] = None
        self.created_at = time.time()
        self.last_seen = time.time()

    def is_expired(self) -> bool:
        """Check if connection has expired"""
        return time.time() - self.last_seen > UDP_CONNECTION_TIMEOUT

    def update_activity(self):
        """Update last seen timestamp"""
        self.last_seen = time.time()


class UDPParser:
    """UDP tracker request/response parser"""

    def __init__(self):
        self.connections: Dict[Tuple[str, int], UDPConnection] = {}

    def parse_request(self, data: bytes, remote_addr: Tuple[str, int]) -> Optional[Dict]:
        """
        Parse UDP tracker request

        Args:
            data: Raw UDP packet data
            remote_addr: (host, port) tuple

        Returns:
            Parsed request parameters or None if invalid
        """
        if len(data) < 16:
            return None

        try:
            # Read the packet
            connection_id = struct.unpack('>Q', data[0:8])[0]
            action = struct.unpack('>I', data[8:12])[0]
            transaction_id = struct.unpack('>I', data[12:16])[0]

            # Basic validation
            if action not in [ACTIONS['CONNECT'], ACTIONS['ANNOUNCE'], ACTIONS['SCRAPE']]:
                return None

            params = {
                'connection_id': connection_id,
                'action': action,
                'transaction_id': transaction_id,
                'remote_addr': remote_addr
            }

            # Parse action-specific data
            if action == ACTIONS['CONNECT']:
                return self._parse_connect_request(params, data[16:])
            elif action == ACTIONS['ANNOUNCE']:
                return self._parse_announce_request(params, data[16:])
            elif action == ACTIONS['SCRAPE']:
                return self._parse_scrape_request(params, data[16:])

        except (struct.error, IndexError):
            return None

        return None

    def _parse_connect_request(self, params: Dict, data: bytes) -> Dict:
        """Parse UDP connect request"""
        # Connect requests don't have additional data
        params['type'] = 'udp'
        return params

    def _parse_announce_request(self, params: Dict, data: bytes) -> Optional[Dict]:
        """Parse UDP announce request"""
        if len(data) < 82:
            return None

        try:
            # Parse announce-specific fields
            info_hash_bytes = data[0:20]
            peer_id_bytes = data[20:40]
            downloaded = struct.unpack('>Q', data[40:48])[0]
            left = struct.unpack('>Q', data[48:56])[0]
            uploaded = struct.unpack('>Q', data[56:64])[0]
            event = struct.unpack('>I', data[64:68])[0]
            ip = struct.unpack('>I', data[68:72])[0]
            key = struct.unpack('>I', data[72:76])[0]
            numwant = struct.unpack('>i', data[76:80])[0]  # -1 means default
            port = struct.unpack('>H', data[80:82])[0]

            # Convert binary data
            params.update({
                'info_hash': bin_to_hex(info_hash_bytes),
                'peer_id': bin_to_hex(peer_id_bytes),
                'downloaded': downloaded,
                'left': left,
                'uploaded': uploaded,
                'event': self._event_id_to_name(event),
                'key': key,
                'numwant': numwant if numwant >= 0 else DEFAULT_ANNOUNCE_PEERS,
                'port': port,
                'type': 'udp'
            })

            # Handle IP (0 means use remote address)
            if ip == 0:
                params['ip'] = params['remote_addr'][0]
            else:
                # Convert from big-endian integer to IP string
                params['ip'] = '.'.join(str((ip >> (24 - 8*i)) & 0xFF) for i in range(4))

            params['addr'] = f"{params['ip']}:{port}"

            return params

        except (struct.error, IndexError):
            return None

    def _parse_scrape_request(self, params: Dict, data: bytes) -> Optional[Dict]:
        """Parse UDP scrape request"""
        # Scrape requests contain one or more info_hashes (20 bytes each)
        if len(data) % 20 != 0 or len(data) == 0:
            return None

        try:
            info_hashes = []
            for i in range(0, len(data), 20):
                info_hash_bytes = data[i:i+20]
                info_hashes.append(bin_to_hex(info_hash_bytes))

            params.update({
                'info_hash': info_hashes,
                'type': 'udp'
            })

            return params

        except Exception:
            return None

    def _event_id_to_name(self, event_id: int) -> str:
        """Convert event ID to event name"""
        event_map = {
            0: 'none',      # No event (periodic update)
            1: 'completed',
            2: 'started',
            3: 'stopped'
        }
        return event_map.get(event_id, 'update')

    def create_connect_response(self, transaction_id: int) -> bytes:
        """Create UDP connect response"""
        connection_id = int(time.time())  # Simple connection ID based on timestamp
        return (
            to_uint32(ACTIONS['CONNECT']) +
            to_uint32(transaction_id) +
            struct.pack('>Q', connection_id)
        )

    def create_announce_response(self, transaction_id: int, interval: int,
                               leechers: int, seeders: int, peers: bytes) -> bytes:
        """Create UDP announce response"""
        return (
            to_uint32(ACTIONS['ANNOUNCE']) +
            to_uint32(transaction_id) +
            to_uint32(interval) +
            to_uint32(leechers) +
            to_uint32(seeders) +
            peers
        )

    def create_scrape_response(self, transaction_id: int, stats_list: list) -> bytes:
        """Create UDP scrape response"""
        response = to_uint32(ACTIONS['SCRAPE']) + to_uint32(transaction_id)

        for stats in stats_list:
            response += (
                to_uint32(stats.get('complete', 0)) +
                to_uint32(stats.get('downloaded', 0)) +
                to_uint32(stats.get('incomplete', 0))
            )

        return response

    def create_error_response(self, transaction_id: int, message: str) -> bytes:
        """Create UDP error response"""
        message_bytes = message.encode('utf-8')
        return (
            to_uint32(ACTIONS['ERROR']) +
            to_uint32(transaction_id) +
            message_bytes
        )

    def get_connection_id(self, remote_addr: Tuple[str, int]) -> Optional[int]:
        """Get connection ID for remote address"""
        conn = self.connections.get(remote_addr)
        if conn and not conn.is_expired():
            conn.update_activity()
            return conn.connection_id
        return None

    def set_connection_id(self, remote_addr: Tuple[str, int], connection_id: int):
        """Set connection ID for remote address"""
        self.connections[remote_addr] = UDPConnection(remote_addr)
        self.connections[remote_addr].connection_id = connection_id
        self.connections[remote_addr].update_activity()

    def cleanup_expired_connections(self):
        """Remove expired UDP connections"""
        expired = [addr for addr, conn in self.connections.items() if conn.is_expired()]
        for addr in expired:
            del self.connections[addr]
