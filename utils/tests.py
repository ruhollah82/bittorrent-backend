import hashlib
from django.test import TestCase, RequestFactory
from django.http import HttpRequest
from unittest.mock import patch, MagicMock

from .helpers import (
    generate_random_string,
    generate_unique_code,
    calculate_sha1_hash,
    calculate_info_hash_from_torrent_data,
    validate_info_hash,
    format_bytes,
    format_credit,
    calculate_ratio,
    get_client_ip,
    is_valid_ip_address,
    generate_peer_id,
    parse_user_agent,
    safe_divide,
    truncate_string,
    validate_username,
    validate_email,
    get_system_info,
    create_success_response,
    create_error_response,
)


class UtilsHelpersTestCase(TestCase):
    """Comprehensive tests for utility helper functions"""

    def test_generate_random_string(self):
        """Test random string generation"""
        # Test default length
        result = generate_random_string()
        self.assertEqual(len(result), 32)
        self.assertIsInstance(result, str)

        # Test custom length
        result = generate_random_string(16)
        self.assertEqual(len(result), 16)

        # Test that different calls produce different results
        result1 = generate_random_string(10)
        result2 = generate_random_string(10)
        self.assertNotEqual(result1, result2)

    def test_generate_unique_code(self):
        """Test unique code generation"""
        result = generate_unique_code()
        self.assertEqual(len(result), 12)
        self.assertTrue(result.isupper() or result.isdigit())

        # Test custom length
        result = generate_unique_code(8)
        self.assertEqual(len(result), 8)

    def test_calculate_sha1_hash(self):
        """Test SHA1 hash calculation"""
        test_data = b"test data"
        expected = hashlib.sha1(test_data).hexdigest()
        result = calculate_sha1_hash(test_data)
        self.assertEqual(result, expected)
        self.assertEqual(len(result), 40)

    def test_calculate_info_hash_from_torrent_data(self):
        """Test info hash calculation from torrent data"""
        test_data = b"torrent data"
        result = calculate_info_hash_from_torrent_data(test_data)
        self.assertIsInstance(result, str)
        self.assertEqual(len(result), 40)

        # Test with invalid data
        result = calculate_info_hash_from_torrent_data(None)
        self.assertEqual(result, "")

    def test_validate_info_hash(self):
        """Test info hash validation"""
        # Valid hash
        valid_hash = "aabbccddeeff00112233445566778899aabbccdd"
        self.assertTrue(validate_info_hash(valid_hash))

        # Invalid length
        self.assertFalse(validate_info_hash("short"))
        self.assertFalse(validate_info_hash("a" * 41))

        # Invalid characters
        self.assertFalse(validate_info_hash("gggggggggggggggggggggggggggggggggggggggg"))

        # Empty string
        self.assertFalse(validate_info_hash(""))
        self.assertFalse(validate_info_hash(None))

    def test_format_bytes(self):
        """Test byte formatting"""
        # Bytes
        self.assertEqual(format_bytes(512), "512 B")

        # Kilobytes
        self.assertEqual(format_bytes(1536), "1.5 KB")

        # Megabytes
        self.assertEqual(format_bytes(1048576), "1.0 MB")

        # Gigabytes
        self.assertEqual(format_bytes(1073741824), "1.0 GB")

    def test_format_credit(self):
        """Test credit formatting"""
        self.assertEqual(format_credit(10.5), "10.50")
        self.assertEqual(format_credit(0.0), "0.00")
        self.assertEqual(format_credit(123.456), "123.46")

    def test_calculate_ratio(self):
        """Test ratio calculation"""
        # Normal ratio
        self.assertEqual(calculate_ratio(100, 50), 2.0)

        # Zero download with upload
        self.assertEqual(calculate_ratio(100, 0), 999.99)

        # Zero download and upload
        self.assertEqual(calculate_ratio(0, 0), 0.0)

        # Very high ratio (should be capped)
        self.assertEqual(calculate_ratio(1000000, 1), 999.99)

    def test_get_client_ip(self):
        """Test client IP extraction"""
        factory = RequestFactory()

        # Direct IP
        request = factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        self.assertEqual(get_client_ip(request), '192.168.1.1')

        # X-Forwarded-For header
        request = factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.1, 198.51.100.1'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        self.assertEqual(get_client_ip(request), '203.0.113.1')

        # No headers (Django test client sets REMOTE_ADDR to 127.0.0.1)
        request = factory.get('/')
        # Remove REMOTE_ADDR to simulate no IP
        if 'REMOTE_ADDR' in request.META:
            del request.META['REMOTE_ADDR']
        self.assertEqual(get_client_ip(request), None)

    def test_is_valid_ip_address(self):
        """Test IP address validation"""
        # Valid IPv4
        self.assertTrue(is_valid_ip_address('192.168.1.1'))
        self.assertTrue(is_valid_ip_address('127.0.0.1'))

        # Valid IPv6
        self.assertTrue(is_valid_ip_address('::1'))
        self.assertTrue(is_valid_ip_address('2001:db8::1'))

        # Invalid IPs
        self.assertFalse(is_valid_ip_address('256.256.256.256'))
        self.assertFalse(is_valid_ip_address('invalid'))
        self.assertFalse(is_valid_ip_address(''))

    def test_generate_peer_id(self):
        """Test peer ID generation"""
        result = generate_peer_id()
        self.assertEqual(len(result), 20)
        self.assertTrue(result.startswith('-qB0001-'))

    def test_parse_user_agent(self):
        """Test user agent parsing"""
        # qBittorrent
        ua = parse_user_agent('qBittorrent/4.3.8')
        self.assertEqual(ua['client'], 'qBittorrent')

        # Transmission
        ua = parse_user_agent('Transmission/3.00')
        self.assertEqual(ua['client'], 'Transmission')

        # uTorrent
        ua = parse_user_agent('uTorrent/3.5.5')
        self.assertEqual(ua['client'], 'uTorrent')

        # Deluge
        ua = parse_user_agent('Deluge/2.0.3')
        self.assertEqual(ua['client'], 'Deluge')

        # Vuze
        ua = parse_user_agent('Vuze/5.7.6')
        self.assertEqual(ua['client'], 'Vuze')

        # Unknown
        ua = parse_user_agent('UnknownClient/1.0')
        self.assertEqual(ua['client'], 'unknown')

        # Empty
        ua = parse_user_agent('')
        self.assertEqual(ua['client'], 'unknown')

    def test_safe_divide(self):
        """Test safe division"""
        # Normal division
        self.assertEqual(safe_divide(10, 2), 5.0)

        # Division by zero with default
        self.assertEqual(safe_divide(10, 0), 0.0)

        # Division by zero with custom default
        self.assertEqual(safe_divide(10, 0, 42.0), 42.0)

        # Type error
        self.assertEqual(safe_divide("10", "2"), 0.0)

    def test_truncate_string(self):
        """Test string truncation"""
        # No truncation needed
        self.assertEqual(truncate_string("short", 10), "short")

        # Truncation with default suffix
        self.assertEqual(truncate_string("very long string that needs truncation", 20), "very long string ...")

        # Truncation with custom suffix
        self.assertEqual(truncate_string("very long string", 10, "***"), "very lo***")

        # Exact length
        self.assertEqual(truncate_string("exact", 5), "exact")

    def test_validate_username(self):
        """Test username validation"""
        # Valid usernames
        valid, msg = validate_username("testuser")
        self.assertTrue(valid)
        self.assertEqual(msg, "")

        valid, msg = validate_username("test_user123")
        self.assertTrue(valid)

        valid, msg = validate_username("test-user")
        self.assertTrue(valid)

        # Invalid usernames
        valid, msg = validate_username("")
        self.assertFalse(valid)
        self.assertEqual(msg, "Username cannot be empty")

        valid, msg = validate_username("ab")
        self.assertFalse(valid)
        self.assertEqual(msg, "Username must be at least 3 characters long")

        valid, msg = validate_username("a" * 31)
        self.assertFalse(valid)
        self.assertEqual(msg, "Username cannot be longer than 30 characters")

        valid, msg = validate_username("test@user")
        self.assertFalse(valid)
        self.assertEqual(msg, "Username can only contain letters, numbers, underscore, and dash")

        valid, msg = validate_username("admin")
        self.assertFalse(valid)
        self.assertEqual(msg, "This username is reserved")

    def test_validate_email(self):
        """Test email validation"""
        # Valid emails
        valid, msg = validate_email("test@example.com")
        self.assertTrue(valid)
        self.assertEqual(msg, "")

        valid, msg = validate_email("user.name+tag@domain.co.uk")
        self.assertTrue(valid)

        # Invalid emails
        valid, msg = validate_email("")
        self.assertFalse(valid)
        self.assertEqual(msg, "Email cannot be empty")

        valid, msg = validate_email("invalid-email")
        self.assertFalse(valid)
        self.assertEqual(msg, "Invalid email format")

        valid, msg = validate_email("@example.com")
        self.assertFalse(valid)

        valid, msg = validate_email("test@")
        self.assertFalse(valid)

    def test_get_system_info(self):
        """Test system info retrieval"""
        try:
            # Test that function returns a dict with expected keys
            result = get_system_info()
            self.assertIsInstance(result, dict)
            self.assertIn('platform', result)
            self.assertIn('python_version', result)

            # Basic checks for known keys
            self.assertIsInstance(result['platform'], str)
            self.assertIsInstance(result['python_version'], str)
        except ImportError:
            # Skip test if psutil is not available
            self.skipTest("psutil not available")

    def test_create_success_response(self):
        """Test success response creation"""
        # Basic response
        result = create_success_response("Operation successful")
        expected = {'success': True, 'message': 'Operation successful'}
        self.assertEqual(result, expected)

        # Response with data
        data = {'user_id': 123, 'credits': 45.67}
        result = create_success_response("User created", data)
        expected = {
            'success': True,
            'message': 'User created',
            'user_id': 123,
            'credits': 45.67
        }
        self.assertEqual(result, expected)

    def test_create_error_response(self):
        """Test error response creation"""
        # Basic error
        result = create_error_response("Something went wrong")
        expected = {'success': False, 'error': 'Something went wrong'}
        self.assertEqual(result, expected)

        # Error with code
        result = create_error_response("Invalid input", "VALIDATION_ERROR")
        expected = {
            'success': False,
            'error': 'Invalid input',
            'error_code': 'VALIDATION_ERROR'
        }
        self.assertEqual(result, expected)
