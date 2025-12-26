"""
Utility functions and helpers for the BitTorrent backend
"""
import hashlib
import hmac
import secrets
import string
from typing import Optional
from django.utils import timezone
from django.conf import settings


def generate_random_string(length: int = 32) -> str:
    """Generate a random string of specified length"""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))


def generate_unique_code(length: int = 12) -> str:
    """Generate a unique code for invite codes"""
    while True:
        code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length))
        # Check uniqueness - this would need to be implemented based on your model
        # For now, just return the generated code
        return code


def calculate_sha1_hash(data: bytes) -> str:
    """Calculate SHA1 hash and return as hex string"""
    return hashlib.sha1(data).hexdigest()


def calculate_info_hash_from_torrent_data(torrent_data: bytes) -> str:
    """Calculate info hash from torrent file data"""
    # This is a simplified implementation
    # In a real implementation, you'd parse the bencoded torrent data
    # and extract the 'info' dictionary, then hash it
    try:
        # For now, just return a hash of the entire data
        return hashlib.sha1(torrent_data).hexdigest()
    except Exception:
        return ""


def validate_info_hash(info_hash: str) -> bool:
    """Validate info hash format (40 character hex)"""
    if not info_hash or len(info_hash) != 40:
        return False

    try:
        int(info_hash, 16)
        return True
    except ValueError:
        return False


def format_bytes(bytes_value: int) -> str:
    """Format bytes to human readable format"""
    if bytes_value < 1024:
        return f"{bytes_value} B"
    elif bytes_value < 1024 * 1024:
        return f"{bytes_value / 1024:.1f} KB"
    elif bytes_value < 1024 * 1024 * 1024:
        return f"{bytes_value / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_value / (1024 * 1024 * 1024):.1f} GB"


def format_credit(amount: float) -> str:
    """Format credit amount with proper precision"""
    return f"{amount:.2f}"


def calculate_ratio(uploaded: int, downloaded: int) -> float:
    """Calculate upload/download ratio"""
    if downloaded == 0:
        return 999.99 if uploaded > 0 else 0.0
    return min(uploaded / downloaded, 999.99)


def get_client_ip(request) -> str:
    """Extract client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def is_valid_ip_address(ip: str) -> bool:
    """Validate IP address format"""
    import ipaddress
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def generate_peer_id() -> str:
    """Generate a peer ID for testing purposes"""
    # BitTorrent peer IDs are 20 bytes
    # Usually start with client identifier like '-qB0001-'
    return f"-qB0001-{generate_random_string(12)}"


def parse_user_agent(user_agent: str) -> dict:
    """Parse user agent string to extract client information"""
    info = {
        'client': 'unknown',
        'version': 'unknown',
        'os': 'unknown'
    }

    if not user_agent:
        return info

    user_agent = user_agent.lower()

    # Detect common BitTorrent clients
    if 'qbittorrent' in user_agent:
        info['client'] = 'qBittorrent'
    elif 'transmission' in user_agent:
        info['client'] = 'Transmission'
    elif 'utorrent' in user_agent or 'bittorrent' in user_agent:
        info['client'] = 'uTorrent'
    elif 'deluge' in user_agent:
        info['client'] = 'Deluge'
    elif 'vuze' in user_agent:
        info['client'] = 'Vuze'

    return info


def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """Safe division that returns default value if divisor is zero"""
    try:
        return a / b if b != 0 else default
    except (ZeroDivisionError, TypeError):
        return default


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate string to specified length with suffix"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def validate_username(username: str) -> tuple[bool, str]:
    """Validate username format and return (is_valid, error_message)"""
    if not username:
        return False, "Username cannot be empty"

    if len(username) < 3:
        return False, "Username must be at least 3 characters long"

    if len(username) > 30:
        return False, "Username cannot be longer than 30 characters"

    # Check for valid characters (letters, numbers, underscore, dash)
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username can only contain letters, numbers, underscore, and dash"

    # Check for reserved words
    reserved_words = ['admin', 'administrator', 'moderator', 'system', 'bot']
    if username.lower() in reserved_words:
        return False, "This username is reserved"

    return True, ""


def validate_email(email: str) -> tuple[bool, str]:
    """Validate email format and return (is_valid, error_message)"""
    import re

    if not email:
        return False, "Email cannot be empty"

    # Basic email regex validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(email_pattern, email):
        return False, "Invalid email format"

    return True, ""


def get_system_info() -> dict:
    """Get basic system information"""
    import platform
    import psutil
    import os

    try:
        return {
            'platform': platform.system(),
            'platform_version': platform.release(),
            'python_version': platform.python_version(),
            'cpu_count': os.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available,
            'disk_total': psutil.disk_usage('/').total,
            'disk_free': psutil.disk_usage('/').free,
        }
    except ImportError:
        # psutil not available
        return {
            'platform': platform.system(),
            'platform_version': platform.release(),
            'python_version': platform.python_version(),
            'cpu_count': os.cpu_count() if hasattr(os, 'cpu_count') else 'unknown',
        }


def create_success_response(message: str, data: dict = None) -> dict:
    """Create standardized success response"""
    response = {'success': True, 'message': message}
    if data:
        response.update(data)
    return response


def create_error_response(message: str, error_code: str = None) -> dict:
    """Create standardized error response"""
    response = {'success': False, 'error': message}
    if error_code:
        response['error_code'] = error_code
    return response
