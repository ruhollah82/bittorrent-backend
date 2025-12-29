"""
Swarm class for managing peers in a single torrent
"""
import time
import random
from collections import OrderedDict
from .common import EVENTS, EVENT_NAMES, DEFAULT_ANNOUNCE_PEERS, MAX_ANNOUNCE_PEERS


class Peer:
    """Represents a peer in the swarm"""

    def __init__(self, peer_id: str, ip: str, port: int, peer_type: str = 'http'):
        self.peer_id = peer_id  # hex string
        self.ip = ip
        self.port = port
        self.type = peer_type  # 'http', 'udp', 'ws'
        self.complete = False  # whether this peer has completed downloading
        self.last_seen = time.time()

    def to_dict(self):
        """Convert peer to dictionary format"""
        return {
            'peer_id': self.peer_id,
            'ip': self.ip,
            'port': self.port,
            'type': self.type,
            'complete': self.complete
        }


class Swarm:
    """
    Manages peers for a single torrent.

    Uses a simple LRU-style cache with OrderedDict for peer management.
    """

    def __init__(self, info_hash: str, max_peers: int = 1000, peer_ttl: int = 1200):
        self.info_hash = info_hash
        self.complete = 0  # number of seeders
        self.incomplete = 0  # number of leechers

        # Peer storage with LRU behavior
        self.peers = OrderedDict()  # peer_addr -> Peer object
        self.max_peers = max_peers
        self.peer_ttl = peer_ttl  # seconds

    def _cleanup_expired_peers(self):
        """Remove peers that haven't been seen recently"""
        current_time = time.time()
        expired_addrs = []

        for addr, peer in self.peers.items():
            if current_time - peer.last_seen > self.peer_ttl:
                expired_addrs.append(addr)
                if peer.complete:
                    self.complete -= 1
                else:
                    self.incomplete -= 1

        for addr in expired_addrs:
            del self.peers[addr]

    def _evict_oldest_peer(self):
        """Remove the least recently used peer when at capacity"""
        if len(self.peers) >= self.max_peers:
            # Remove the first item (least recently used)
            oldest_addr, oldest_peer = next(iter(self.peers.items()))
            if oldest_peer.complete:
                self.complete -= 1
            else:
                self.incomplete -= 1
            del self.peers[oldest_addr]

    def announce(self, params: dict) -> dict:
        """
        Handle an announce request from a peer

        Args:
            params: Dictionary containing announce parameters:
                - peer_id: hex string
                - ip: IP address
                - port: port number
                - left: bytes left to download
                - event: 'started', 'stopped', 'completed', 'update', 'paused'
                - type: 'http', 'udp', 'ws'
                - numwant: number of peers to return

        Returns:
            Dictionary with response data
        """
        self._cleanup_expired_peers()

        peer_addr = f"{params['ip']}:{params['port']}"
        peer_id = params['peer_id']
        event = params.get('event', 'update')
        left = params.get('left', 0)
        numwant = min(params.get('numwant', DEFAULT_ANNOUNCE_PEERS), MAX_ANNOUNCE_PEERS)

        # Mark peer as recently used (move to end)
        if peer_addr in self.peers:
            self.peers.move_to_end(peer_addr)
            peer = self.peers[peer_addr]
        else:
            peer = None

        # Handle different events
        if event == 'started':
            self._handle_started(params, peer, peer_addr)
        elif event == 'stopped':
            self._handle_stopped(params, peer, peer_addr)
        elif event == 'completed':
            self._handle_completed(params, peer, peer_addr)
        elif event == 'update':
            self._handle_update(params, peer, peer_addr)
        elif event == 'paused':
            self._handle_paused(params, peer, peer_addr)
        else:
            raise ValueError(f"Invalid event: {event}")

        # Get peers to return
        peers = self._get_peers(numwant, peer_id)

        return {
            'complete': self.complete,
            'incomplete': self.incomplete,
            'peers': peers
        }

    def _handle_started(self, params, peer, peer_addr):
        """Handle 'started' event"""
        if peer:
            # Peer already exists, treat as update
            return self._handle_update(params, peer, peer_addr)

        # Add new peer
        left = params.get('left', 0)
        new_peer = Peer(
            peer_id=params['peer_id'],
            ip=params['ip'],
            port=params['port'],
            peer_type=params.get('type', 'http')
        )
        new_peer.complete = (left == 0)

        if new_peer.complete:
            self.complete += 1
        else:
            self.incomplete += 1

        # Add to cache, evicting if necessary
        self._evict_oldest_peer()
        self.peers[peer_addr] = new_peer
        self.peers.move_to_end(peer_addr)  # Mark as recently used

    def _handle_stopped(self, params, peer, peer_addr):
        """Handle 'stopped' event"""
        if not peer:
            return  # Peer not in swarm, ignore

        # Remove peer from swarm
        if peer.complete:
            self.complete -= 1
        else:
            self.incomplete -= 1

        del self.peers[peer_addr]

    def _handle_completed(self, params, peer, peer_addr):
        """Handle 'completed' event"""
        if not peer:
            # Peer not in swarm, treat as started
            return self._handle_started(params, peer, peer_addr)

        if peer.complete:
            # Already completed, treat as update
            return self._handle_update(params, peer, peer_addr)

        # Peer just completed
        self.complete += 1
        self.incomplete -= 1
        peer.complete = True
        self.peers.move_to_end(peer_addr)  # Mark as recently used

    def _handle_update(self, params, peer, peer_addr):
        """Handle 'update' event"""
        if not peer:
            # Peer not in swarm, treat as started
            return self._handle_started(params, peer, peer_addr)

        # Update peer info
        left = params.get('left', 0)
        if not peer.complete and left == 0:
            # Peer just completed during update
            self.complete += 1
            self.incomplete -= 1
            peer.complete = True

        peer.last_seen = time.time()
        self.peers.move_to_end(peer_addr)  # Mark as recently used

    def _handle_paused(self, params, peer, peer_addr):
        """Handle 'paused' event - treat as update"""
        return self._handle_update(params, peer, peer_addr)

    def _get_peers(self, numwant: int, exclude_peer_id: str = None) -> list:
        """
        Get random peers for the requesting peer

        Args:
            numwant: Number of peers to return
            exclude_peer_id: Peer ID to exclude (don't return self)

        Returns:
            List of peer dictionaries
        """
        # Get all peer addresses and shuffle them
        peer_addrs = list(self.peers.keys())
        random.shuffle(peer_addrs)

        peers = []
        for addr in peer_addrs:
            if len(peers) >= numwant:
                break

            peer = self.peers[addr]
            if peer.peer_id == exclude_peer_id:
                continue  # Don't return self

            peers.append(peer.to_dict())

        return peers

    def scrape(self) -> dict:
        """Return scrape statistics"""
        return {
            'complete': self.complete,
            'incomplete': self.incomplete,
            'downloaded': self.complete  # Lower bound estimate
        }

    def get_peer_count(self) -> int:
        """Get total number of active peers"""
        return len(self.peers)
