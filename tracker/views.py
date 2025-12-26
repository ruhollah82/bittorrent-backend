import hashlib
import hmac
import secrets
from urllib.parse import unquote
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
import bencode

from security.models import AnnounceLog
from torrents.models import Torrent, Peer, TorrentStats
from accounts.models import User, AuthToken
from credits.models import CreditTransaction
from security.models import SuspiciousActivity, RateLimit, IPBlock
from logging_monitoring.models import SystemLog
from credits.models import CreditTransaction


def get_client_ip(request):
    """دریافت IP آدرس کلاینت"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def validate_announce_params(params):
    """بررسی پارامترهای announce"""
    required_params = ['info_hash', 'peer_id', 'port', 'uploaded', 'downloaded', 'left', 'compact', 'event']

    for param in required_params:
        if param not in params:
            return False, f"Missing parameter: {param}"

    # بررسی فرمت info_hash (40 کاراکتر hex)
    info_hash = params.get('info_hash', '')
    if not (len(info_hash) == 40 and all(c in '0123456789abcdefABCDEF' for c in info_hash)):
        return False, "Invalid info_hash format"

    # بررسی peer_id
    peer_id = params.get('peer_id', '')
    if len(peer_id) != 20:
        return False, "Invalid peer_id length"

    # بررسی port
    try:
        port = int(params.get('port', 0))
        if not (1 <= port <= 65535):
            return False, "Invalid port number"
    except ValueError:
        return False, "Invalid port format"

    # بررسی مقادیر عددی
    for param in ['uploaded', 'downloaded', 'left']:
        try:
            value = int(params.get(param, -1))
            if value < 0:
                return False, f"Invalid {param} value"
        except ValueError:
            return False, f"Invalid {param} format"

    return True, "OK"


def validate_auth_token(request, info_hash):
    """بررسی اعتبار توکن احراز هویت"""
    auth_token = request.GET.get('auth_token')
    if not auth_token:
        return None, "Missing auth_token"

    try:
        token = AuthToken.objects.get(token=auth_token, is_active=True)
    except AuthToken.DoesNotExist:
        return None, "Invalid auth_token"

    # بررسی تاریخ انقضا
    if token.is_expired():
        return None, "Expired auth_token"

    # بررسی IP binding
    client_ip = get_client_ip(request)
    if token.ip_bound and token.ip_bound != client_ip:
        return None, "IP address mismatch"

    # بروزرسانی last_used
    token.last_used = timezone.now()
    token.save(update_fields=['last_used'])

    return token.user, "OK"


def check_rate_limit(identifier, action, max_requests, window_seconds):
    """بررسی rate limiting"""
    cache_key = f"ratelimit:{action}:{identifier}"
    current_time = timezone.now().timestamp()

    # دریافت داده‌های موجود
    data = cache.get(cache_key, {'count': 0, 'window_start': current_time})

    # بررسی بازه زمانی
    if current_time - data['window_start'] > window_seconds:
        data = {'count': 0, 'window_start': current_time}

    # افزایش شمارنده
    data['count'] += 1

    # ذخیره در cache
    cache.set(cache_key, data, window_seconds)

    # بررسی محدودیت
    if data['count'] > max_requests:
        return False

    return True


@csrf_exempt
@require_GET
def announce(request):
    """
    BitTorrent Tracker Announce Endpoint

    پارامترهای مورد انتظار:
    - info_hash: SHA1 hash تورنت
    - peer_id: ID کلاینت
    - port: پورت کلاینت
    - uploaded: حجم آپلود شده
    - downloaded: حجم دانلود شده
    - left: حجم باقیمانده
    - compact: فرمت compact (1 یا 0)
    - event: started|stopped|completed
    - auth_token: توکن احراز هویت
    """

    try:
        # دریافت پارامترها
        params = request.GET.copy()

        # بررسی پارامترهای پایه
        is_valid, error_msg = validate_announce_params(params)
        if not is_valid:
            return create_bencoded_response({'failure reason': error_msg})

        # بررسی IP blocking
        client_ip = get_client_ip(request)
        if IPBlock.objects.filter(ip_address=client_ip, is_active=True).exists():
            return create_bencoded_response({'failure reason': 'IP blocked'})

        # بررسی rate limiting
        if not check_rate_limit(client_ip, 'announce', settings.BITTORRENT_SETTINGS['MAX_ANNOUNCE_RATE'], 60):
            return create_bencoded_response({'failure reason': 'Rate limit exceeded'})

        # بررسی توکن احراز هویت
        user, auth_error = validate_auth_token(request, params['info_hash'])
        if not user:
            return create_bencoded_response({'failure reason': auth_error})

        # بررسی کاربر مسدود شده
        if user.is_banned:
            return create_bencoded_response({'failure reason': 'User banned'})

        # دریافت تورنت
        info_hash = params['info_hash'].lower()
        try:
            torrent = Torrent.objects.get(info_hash=info_hash)
        except Torrent.DoesNotExist:
            return create_bencoded_response({'failure reason': 'Torrent not found'})

        # بررسی دسترسی کاربر به تورنت
        if torrent.is_private and torrent.created_by != user:
            # بررسی credit کافی برای دانلود
            torrent_size_gb = torrent.size / (1024 ** 3)
            required_credit = torrent_size_gb

            if user.available_credit < required_credit:
                return create_bencoded_response({'failure reason': f'Insufficient credit. Required: {required_credit:.2f} GB, Available: {user.available_credit:.2f} GB'})

            # بررسی محدودیت تورنت
            active_torrents = user.peers.filter(state__in=['started', 'completed']).count()
            if active_torrents >= user.max_torrents:
                return create_bencoded_response({'failure reason': f'Maximum torrents reached. Current: {active_torrents}, Max: {user.max_torrents}'})

            # بررسی ratio برای کاربران با دانلود زیاد
            if user.ratio < 0.1 and user.lifetime_download > 1024 * 1024 * 1024:  # 1GB
                return create_bencoded_response({'failure reason': 'Ratio too low for downloading'})

        # پردازش announce
        with transaction.atomic():
            response = process_announce(user, torrent, params, client_ip, request.META.get('HTTP_USER_AGENT', ''))

        return response

    except Exception as e:
        # لاگ خطا
        SystemLog.objects.create(
            category='tracker',
            level='error',
            message=f'Announce error: {str(e)}',
            details={'params': dict(request.GET), 'ip': get_client_ip(request)},
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        return create_bencoded_response({'failure reason': 'Internal server error'})


def process_announce(user, torrent, params, client_ip, user_agent):
    """پردازش درخواست announce"""

    peer_id = params['peer_id']
    port = int(params['port'])
    uploaded = int(params['uploaded'])
    downloaded = int(params['downloaded'])
    left = int(params['left'])
    event = params.get('event', 'started')
    numwant = min(int(params.get('numwant', 50)), 100)  # حداکثر 100 peer

    # بروزرسانی یا ایجاد peer
    peer, created = Peer.objects.get_or_create(
        torrent=torrent,
        user=user,
        defaults={
            'peer_id': peer_id,
            'ip_address': client_ip,
            'port': port,
            'uploaded': uploaded,
            'downloaded': downloaded,
            'left': left,
            'state': event,
            'is_seeder': left == 0,
            'user_agent': user_agent,
        }
    )

    # بررسی فعالیت‌های مشکوک پیشرفته
    suspicious_reasons = []

    # اگر peer وجود داشت، بروزرسانی اطلاعات
    if not created:
        # محاسبه تغییرات
        upload_diff = uploaded - peer.uploaded
        download_diff = downloaded - peer.downloaded

        # بررسی فعالیت‌های مشکوک پیشرفته
        suspicious_reasons = []

        # بررسی مقادیر منفی
        if upload_diff < 0 or download_diff < 0:
            suspicious_reasons.append('negative_values')

        # بررسی تغییرات غیرواقعی
        if upload_diff > torrent.size * 0.1:  # بیش از ۱۰% اندازه تورنت در یک announce
            suspicious_reasons.append('excessive_upload')

        if download_diff > torrent.size * 0.1:  # بیش از ۱۰% اندازه تورنت در یک announce
            suspicious_reasons.append('excessive_download')

        # بررسی الگوی announce (بیش از ۱ announce در دقیقه)
        recent_announces = AnnounceLog.objects.filter(
            user=user,
            timestamp__gte=timezone.now() - timezone.timedelta(minutes=1)
        ).count()

        if recent_announces > 1:
            suspicious_reasons.append('frequent_announces')

        # بررسی peer_id های مشکوک
        if len(peer_id) != 20 or not all(c.isalnum() or c in '.-' for c in peer_id):
            suspicious_reasons.append('invalid_peer_id')

        # بررسی IP spoofing (تغییر IP مکرر)
        recent_ips = set(AnnounceLog.objects.filter(
            user=user,
            timestamp__gte=timezone.now() - timezone.timedelta(hours=1)
        ).values_list('ip_address', flat=True)[:10])

        if len(recent_ips) > 3:  # بیش از ۳ IP مختلف در ۱ ساعت
            suspicious_reasons.append('ip_spoofing')

        # ایجاد فعالیت مشکوک اگر دلایل وجود داشته باشد
        if suspicious_reasons:
            severity = 'critical' if len(suspicious_reasons) > 2 else 'high' if len(suspicious_reasons) > 1 else 'medium'

            SuspiciousActivity.objects.create(
                user=user,
                activity_type='announce_anomaly',
                severity=severity,
                description=f'Suspicious announce detected: {", ".join(suspicious_reasons)}',
                details={
                    'upload_diff': upload_diff,
                    'download_diff': download_diff,
                    'recent_announces': recent_announces,
                    'peer_id': peer_id,
                    'ip_count': len(recent_ips),
                    'reasons': suspicious_reasons
                },
                ip_address=client_ip,
                torrent=torrent
            )

            # ذخیره دلایل مشکوک برای استفاده در لاگ announce

        # بروزرسانی آمار کاربر
        user.lifetime_upload += max(0, upload_diff)
        user.lifetime_download += max(0, download_diff)
        user.save(update_fields=['lifetime_upload', 'lifetime_download'])

        # بروزرسانی credit
        if upload_diff > 0:
            # محاسبه credit بر اساس آپلود
            uploaded_gb = upload_diff / (1024 ** 3)
            base_credit = uploaded_gb * settings.BITTORRENT_SETTINGS['CREDIT_MULTIPLIER']
            # اعمال ضریب کاربر
            final_credit = base_credit * float(user.download_multiplier)

            from decimal import Decimal
            CreditTransaction.objects.create(
                user=user,
                torrent=torrent,
                transaction_type='upload',
                amount=Decimal(str(final_credit)),
                description=f'Upload credit: {uploaded_gb:.2f} GB x {user.download_multiplier} = {final_credit:.2f}'
            )

        # بروزرسانی peer
        peer.peer_id = peer_id
        peer.ip_address = client_ip
        peer.port = port
        peer.uploaded = uploaded
        peer.downloaded = downloaded
        peer.left = left
        peer.state = event
        peer.is_seeder = left == 0
        peer.last_announced = timezone.now()
        peer.user_agent = user_agent
        peer.save()

    # بروزرسانی آمار تورنت
    update_torrent_stats(torrent)

    # لاگ announce
    announce_log = AnnounceLog.objects.create(
        user=user,
        torrent=torrent,
        event=event,
        uploaded=uploaded,
        downloaded=downloaded,
        left=left,
        ip_address=client_ip,
        port=port,
        peer_id=peer_id,
        user_agent=user_agent,
        is_suspicious=bool(suspicious_reasons),
        suspicious_reason=', '.join(suspicious_reasons) if suspicious_reasons else ''
    )

    # ایجاد لیست peerها
    peers = get_peer_list(torrent, user, numwant, params.get('compact') == '1')

    # ایجاد پاسخ
    response = {
        'interval': settings.BITTORRENT_SETTINGS['TRACKER_ANNOUNCE_INTERVAL'],
        'min interval': 300,  # حداقل 5 دقیقه
        'peers': peers,
    }

    # اگر تورنت کامل شده
    if event == 'completed':
        response['complete'] = torrent.stats.completed if hasattr(torrent, 'stats') else 0

    return create_bencoded_response(response)


def update_torrent_stats(torrent):
    """بروزرسانی آمار تورنت"""
    try:
        stats = torrent.stats
    except TorrentStats.DoesNotExist:
        stats = TorrentStats.objects.create(torrent=torrent)

    # محاسبه آمار از peerها
    active_peers = torrent.peers.filter(
        last_announced__gte=timezone.now() - timezone.timedelta(hours=1)
    )

    stats.seeders = active_peers.filter(is_seeder=True).count()
    stats.leechers = active_peers.filter(is_seeder=False).count()
    stats.last_updated = timezone.now()
    stats.save()


def get_peer_list(torrent, exclude_user, numwant, compact=False):
    """ایجاد لیست peerها"""

    # دریافت peerهای فعال (آخرین announce در ۱ ساعت گذشته)
    active_peers = torrent.peers.filter(
        last_announced__gte=timezone.now() - timezone.timedelta(hours=1)
    ).exclude(user=exclude_user)[:numwant]

    if compact:
        # فرمت compact
        peer_list = b''
        for peer in active_peers:
            ip_parts = peer.ip_address.split('.')
            port_bytes = peer.port.to_bytes(2, 'big')
            peer_list += bytes([int(ip_parts[0]), int(ip_parts[1]), int(ip_parts[2]), int(ip_parts[3])]) + port_bytes
        return peer_list
    else:
        # فرمت dictionary
        peer_list = []
        for peer in active_peers:
            peer_list.append({
                'ip': peer.ip_address,
                'port': peer.port,
                'peer id': peer.peer_id,
            })
        return peer_list


@csrf_exempt
@require_GET
def scrape(request):
    """
    BitTorrent Tracker Scrape Endpoint

    پارامترها:
    - info_hash: لیست SHA1 hash تورنت‌ها (اختیاری)
    - auth_token: توکن احراز هویت
    """

    try:
        # بررسی توکن احراز هویت
        user, auth_error = validate_auth_token(request, None)
        if not user:
            return create_bencoded_response({'failure reason': auth_error})

        # بررسی rate limiting
        client_ip = get_client_ip(request)
        if not check_rate_limit(client_ip, 'scrape', 10, 60):  # حداکثر ۱۰ درخواست در دقیقه
            return create_bencoded_response({'failure reason': 'Rate limit exceeded'})

        # دریافت لیست تورنت‌ها
        info_hashes = request.GET.getlist('info_hash', [])

        # اگر هیچ info_hash مشخص نشده، تمام تورنت‌ها
        if not info_hashes:
            torrents = Torrent.objects.filter(is_active=True)
        else:
            # تبدیل به lowercase
            info_hashes = [h.lower() for h in info_hashes]
            torrents = Torrent.objects.filter(info_hash__in=info_hashes, is_active=True)

        # ایجاد پاسخ
        files = {}
        for torrent in torrents:
            try:
                stats = torrent.stats
                files[torrent.info_hash.upper()] = {
                    'complete': stats.seeders,
                    'downloaded': stats.completed,
                    'incomplete': stats.leechers,
                }
            except TorrentStats.DoesNotExist:
                files[torrent.info_hash.upper()] = {
                    'complete': 0,
                    'downloaded': 0,
                    'incomplete': 0,
                }

        response = {'files': files}

        return create_bencoded_response(response)

    except Exception as e:
        # لاگ خطا
        SystemLog.objects.create(
            category='tracker',
            level='error',
            message=f'Scrape error: {str(e)}',
            details={'params': dict(request.GET), 'ip': get_client_ip(request)},
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        return create_bencoded_response({'failure reason': 'Internal server error'})


def create_bencoded_response(data):
    """ایجاد پاسخ bencoded"""
    try:
        bencoded_data = bencode.encode(data)
        return HttpResponse(bencoded_data, content_type='text/plain')
    except Exception as e:
        # در صورت خطا، پاسخ ساده
        error_data = {'failure reason': 'Encoding error'}
        bencoded_error = bencode.encode(error_data)
        return HttpResponse(bencoded_error, content_type='text/plain')