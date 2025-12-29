"""
Common constants and utilities for BitTorrent tracker implementation
"""
import struct
import re
import binascii
from urllib.parse import unquote


# Regular expressions for IP validation
IPV4_RE = re.compile(r'^[\d.]+$')
IPV6_RE = re.compile(r'^[\da-fA-F:]+$')
REMOVE_IPV4_MAPPED_IPV6_RE = re.compile(r'^::ffff:')

# BitTorrent tracker constants
CONNECTION_ID = b'\x00\x00\x04\x17\x27\x10\x19\x80'  # 0x41727101980
ACTIONS = {
    'CONNECT': 0,
    'ANNOUNCE': 1,
    'SCRAPE': 2,
    'ERROR': 3
}

EVENTS = {
    'update': 0,
    'completed': 1,
    'started': 2,
    'stopped': 3,
    'paused': 4
}

EVENT_IDS = {
    0: 'update',
    1: 'completed',
    2: 'started',
    3: 'stopped',
    4: 'paused'
}

EVENT_NAMES = {
    'update': 'update',
    'completed': 'complete',
    'started': 'start',
    'stopped': 'stop',
    'paused': 'pause'
}

# Default values
DEFAULT_ANNOUNCE_PEERS = 50
MAX_ANNOUNCE_PEERS = 82
REQUEST_TIMEOUT = 15000
DESTROY_TIMEOUT = 1000

# UDP specific constants
UDP_CONNECTION_TIMEOUT = 60000  # 60 seconds
UDP_ANNOUNCE_TIMEOUT = 30000    # 30 seconds


def to_uint32(n: int) -> bytes:
    """Convert integer to 32-bit unsigned integer bytes (big-endian)"""
    return struct.pack('>I', n)


def bin_to_hex(data: bytes) -> str:
    """Convert binary data to hex string"""
    return binascii.hexlify(data).decode('ascii')


def hex_to_bin(hex_str: str) -> bytes:
    """Convert hex string to binary data"""
    return binascii.unhexlify(hex_str)


def parse_querystring(q: str) -> dict:
    """
    Parse query string using unescape instead of decodeURIComponent
    since BitTorrent clients send non-UTF8 querystrings
    """
    if not q:
        return {}

    params = {}
    for pair in q.split('&'):
        if '=' in pair:
            key, value = pair.split('=', 1)
            # Use unquote to handle URL-encoded binary data
            try:
                params[key] = unquote(value, encoding='latin-1')
            except UnicodeDecodeError:
                # Fallback for corrupted UTF-8 data
                params[key] = value
        else:
            params[pair] = ''

    return params


def compact_ip_port(ip: str, port: int) -> bytes:
    """Convert IP and port to compact binary format"""
    if IPV6_RE.match(ip):
        # IPv6
        ip_bytes = binascii.unhexlify(ip.replace(':', ''))
        if len(ip_bytes) != 16:
            raise ValueError(f"Invalid IPv6 address: {ip}")
    else:
        # IPv4
        parts = ip.split('.')
        if len(parts) != 4:
            raise ValueError(f"Invalid IPv4 address: {ip}")
        ip_bytes = bytes([int(part) for part in parts])

    port_bytes = struct.pack('>H', port)
    return ip_bytes + port_bytes


def parse_compact_peers(compact_data: bytes) -> list:
    """Parse compact peer list back to IP:port format"""
    if len(compact_data) % 6 != 0:
        raise ValueError("Invalid compact peer data length")

    peers = []
    for i in range(0, len(compact_data), 6):
        ip_bytes = compact_data[i:i+4]
        port_bytes = compact_data[i+4:i+6]

        ip = '.'.join(str(b) for b in ip_bytes)
        port = struct.unpack('>H', port_bytes)[0]
        peers.append({'ip': ip, 'port': port})

    return peers
