from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Count, Sum, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample

from .models import Torrent, TorrentStats, Peer, Category
from .serializers import (
    TorrentSerializer, TorrentStatsSerializer,
    TorrentDetailSerializer, PeerSerializer
)
from credits.models import CreditTransaction
from accounts.models import User
from utils.helpers import get_client_ip


@extend_schema(
    tags=['Torrent Management'],
    summary='List Torrents',
    description='Get a list of all available torrents with optional filtering.',
    parameters=[
        OpenApiParameter(
            name='category',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Filter torrents by category'
        ),
        OpenApiParameter(
            name='search',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Search torrents by name or description'
        ),
    ],
    responses={
        200: TorrentSerializer(many=True)
    }
)
class TorrentListView(generics.ListAPIView):
    """List all available torrents with filtering options"""

    serializer_class = TorrentSerializer
    permission_classes = [permissions.IsAuthenticated]
    paginate_by = 20

    def get_queryset(self):
        queryset = Torrent.objects.filter(is_active=True)

        # فیلترها
        category = self.request.query_params.get('category')
        if category:
            # Try to filter by category ID first, then by slug, then by name
            try:
                category_id = int(category)
                queryset = queryset.filter(category_id=category_id)
            except ValueError:
                # Not a number, try slug or name
                queryset = queryset.filter(
                    Q(category__slug=category) | Q(category__name=category)
                )

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )

        # مرتب‌سازی
        order_by = self.request.query_params.get('order_by', '-created_at')
        if order_by in ['name', '-name', 'size', '-size', 'created_at', '-created_at']:
            queryset = queryset.order_by(order_by)

        return queryset


class TorrentDetailView(generics.RetrieveAPIView):
    """نمای جزئیات تورنت"""

    serializer_class = TorrentDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Torrent.objects.filter(is_active=True)
    lookup_field = 'info_hash'


class TorrentStatsView(generics.RetrieveAPIView):
    """نمای آمار تورنت"""

    serializer_class = TorrentStatsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        torrent_id = self.kwargs['info_hash']
        torrent = get_object_or_404(Torrent, info_hash=torrent_id, is_active=True)
        stats, created = TorrentStats.objects.get_or_create(torrent=torrent)
        return stats


@extend_schema(
    tags=['Torrent Management'],
    summary='Upload Torrent',
    description='Upload a new torrent file with metadata parsing and credit rewards.',
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'torrent_file': {
                    'type': 'string',
                    'format': 'binary',
                    'description': 'The .torrent file to upload'
                },
                'name': {
                    'type': 'string',
                    'description': 'Custom name for the torrent (optional)'
                },
                'description': {
                    'type': 'string',
                    'description': 'Torrent description'
                },
                'category': {
                    'type': 'string',
                    'description': 'Torrent category'
                },
                'is_private': {
                    'type': 'boolean',
                    'description': 'Whether the torrent is private'
                },
                'tags': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'List of tags for the torrent'
                }
            },
            'required': ['torrent_file']
        }
    },
    responses={
        201: OpenApiExample(
            'Upload Success',
            value={
                'message': 'Torrent uploaded successfully',
                'torrent': {
                    'id': 1,
                    'info_hash': 'aabbccddeeff00112233445566778899aabbccdd',
                    'name': 'Example Torrent',
                    'size': 104857600,
                    'category': 'software',
                    'is_private': False
                }
            }
        ),
        400: OpenApiExample(
            'Upload Failed',
            value={'error': 'No torrent file provided'}
        ),
        409: OpenApiExample(
            'Duplicate Torrent',
            value={'error': 'Torrent already exists'}
        )
    }
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def upload_torrent(request):
    """Upload a new torrent file with automatic metadata parsing"""
    if request.method != 'POST':
        return Response({'error': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    # Check if user is authenticated
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        # Get uploaded file
        torrent_file = request.FILES.get('torrent_file')
        if not torrent_file:
            return Response({'error': 'No torrent file provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate file type
        if not torrent_file.name.endswith('.torrent'):
            return Response({'error': 'File must be a .torrent file'}, status=status.HTTP_400_BAD_REQUEST)

        # Read and parse torrent file
        torrent_data = torrent_file.read()

        # Parse bencoded data
        try:
            import bencode
            torrent_dict = bencode.decode(torrent_data)
        except ImportError:
            return Response({'error': 'Bencode parsing not available'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({'error': f'Invalid torrent file: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        # Extract required information
        if 'info' not in torrent_dict:
            return Response({'error': 'Invalid torrent file: missing info dictionary'}, status=status.HTTP_400_BAD_REQUEST)

        info_dict = torrent_dict['info']

        # Calculate info hash
        import hashlib
        info_hash = hashlib.sha1(bencode.encode(info_dict)).hexdigest()

        # Check if torrent already exists
        existing_torrent = Torrent.objects.filter(info_hash=info_hash).first()
        if existing_torrent:
            if existing_torrent.is_active:
                # Active torrent exists - reject upload
                return Response({'error': 'Torrent already exists'}, status=status.HTTP_409_CONFLICT)
            else:
                # Inactive torrent exists - reactivate it
                existing_torrent.is_active = True
                existing_torrent.save()

                # Log reactivation
                from logging_monitoring.models import SystemLog
                SystemLog.objects.create(
                    category='torrent',
                    level='info',
                    message=f'Torrent reactivated: {existing_torrent.name}',
                    details={
                        'torrent_id': existing_torrent.id,
                        'info_hash': existing_torrent.info_hash,
                        'reactivated_by': request.user.username
                    },
                    user=request.user
                )

                return Response({
                    'success': True,
                    'message': f'Torrent {existing_torrent.name} has been reactivated',
                    'torrent': {
                        'id': existing_torrent.id,
                        'name': existing_torrent.name,
                        'info_hash': existing_torrent.info_hash,
                        'size': existing_torrent.size,
                        'created_at': existing_torrent.created_at
                    }
                })

        # Extract metadata
        name = info_dict.get('name', '').decode('utf-8') if isinstance(info_dict.get('name'), bytes) else info_dict.get('name', 'Unknown')
        piece_length = info_dict.get('piece length', 0)
        pieces = info_dict.get('pieces', b'')
        files_count = 1

        # Calculate total size
        if 'files' in info_dict:
            # Multi-file torrent
            total_size = sum(file_info['length'] for file_info in info_dict['files'])
            files_count = len(info_dict['files'])
        else:
            # Single file torrent
            total_size = info_dict.get('length', 0)

        # Get form data
        description = request.POST.get('description', '')
        category_input = request.POST.get('category')
        category = None
        if category_input:
            try:
                # Try to get category by ID first
                category_id = int(category_input)
                category = Category.objects.get(id=category_id, is_active=True)
            except (ValueError, Category.DoesNotExist):
                # Try to get category by slug or name
                try:
                    category = Category.objects.get(
                        Q(slug=category_input) | Q(name=category_input),
                        is_active=True
                    )
                except Category.DoesNotExist:
                    # Invalid category, set to None
                    pass

        is_private = request.POST.get('is_private', 'false').lower() == 'true'

        # Create torrent record
        torrent = Torrent.objects.create(
            info_hash=info_hash,
            name=name,
            description=description,
            size=total_size,
            files_count=files_count,
            created_by=request.user,
            is_active=True,
            is_private=is_private,
            category=category,
            piece_length=piece_length,
            pieces_hash=pieces.hex() if pieces else '',
            announce_url=torrent_dict.get('announce', '').decode('utf-8') if isinstance(torrent_dict.get('announce'), bytes) else torrent_dict.get('announce', ''),
            comment=info_dict.get('comment', '').decode('utf-8') if isinstance(info_dict.get('comment'), bytes) else info_dict.get('comment', ''),
            created_by_client=request.POST.get('created_by_client', ''),
            tags=request.POST.getlist('tags', [])
        )

        # Create initial stats
        from .models import TorrentStats
        TorrentStats.objects.create(torrent=torrent)

        # Award upload credits
        from credits.models import CreditTransaction
        from django.conf import settings
        from decimal import Decimal

        # Calculate credits based on torrent size
        # 1 credit per GB uploaded
        torrent_size_gb = Decimal(total_size) / Decimal(1024 ** 3)
        multiplier = Decimal(str(getattr(settings, 'BITTORRENT_SETTINGS', {}).get('UPLOAD_CREDIT_MULTIPLIER', 1.0)))
        upload_credits = (torrent_size_gb * multiplier).quantize(Decimal('0.01'))  # Round to 2 decimal places

        if upload_credits > 0:
            CreditTransaction.objects.create(
                user=request.user,
                torrent=torrent,
                transaction_type='upload',
                amount=upload_credits,
                description=f'Upload credit for torrent: {name} ({torrent_size_gb:.2f} GB)'
            )

        # Log the upload
        from logging_monitoring.models import UserActivity, SystemLog
        UserActivity.objects.create(
            user=request.user,
            activity_type='torrent_upload',
            description=f'Uploaded torrent: {name} (+{upload_credits:.2f} credits)',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={'torrent_id': torrent.id, 'info_hash': info_hash, 'credits_earned': upload_credits}
        )

        SystemLog.objects.create(
            category='tracker',
            level='info',
            message=f'User {request.user.username} uploaded torrent: {name} (+{upload_credits:.2f} credits)',
            user=request.user,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={'torrent_id': torrent.id, 'size': total_size, 'credits_earned': upload_credits}
        )

        return Response({
            'message': 'Torrent uploaded successfully',
            'torrent': {
                'id': torrent.id,
                'info_hash': torrent.info_hash,
                'name': torrent.name,
                'size': torrent.size,
                'category': torrent.category,
                'is_private': torrent.is_private
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        # Log error
        from logging_monitoring.models import SystemLog
        SystemLog.objects.create(
            category='tracker',
            level='error',
            message=f'Torrent upload error: {str(e)}',
            user=request.user if request.user.is_authenticated else None,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={'error': str(e)}
        )

        return Response({
            'error': f'Upload failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def torrent_categories(request):
    """دریافت لیست دسته‌بندی‌های تورنت با تعداد تورنت‌های هر دسته"""

    # Get all active categories with torrent counts
    categories_with_counts = Category.objects.filter(
        is_active=True
    ).annotate(
        count=Count('torrents', filter=Q(torrents__is_active=True))
    ).values(
        'id', 'name', 'slug', 'description', 'icon', 'color', 'count'
    ).order_by('sort_order')

    return Response({
        'categories': list(categories_with_counts),
        'total_categories': len(categories_with_counts)
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def categories_list(request):
    """دریافت لیست ساده دسته‌بندی‌ها برای استفاده در فرم‌ها"""

    categories = Category.objects.filter(
        is_active=True
    ).values('id', 'name', 'slug', 'icon', 'color').order_by('sort_order')

    return Response({
        'categories': list(categories)
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def torrent_popular(request):
    """دریافت تورنت‌های محبوب"""

    # تورنت‌هایی با بیشترین peerها در ۲۴ ساعت گذشته
    popular_torrents = Torrent.objects.filter(
        is_active=True,
        peers__last_announced__gte=timezone.now() - timezone.timedelta(hours=24)
    ).annotate(
        active_peers=Count('peers', filter=Q(
            peers__last_announced__gte=timezone.now() - timezone.timedelta(hours=24)
        ))
    ).order_by('-active_peers')[:20]

    serializer = TorrentSerializer(popular_torrents, many=True)
    return Response({
        'popular_torrents': serializer.data
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_torrents(request):
    """دریافت تورنت‌های کاربر"""

    user_torrents = Torrent.objects.filter(
        created_by=request.user,
        is_active=True
    ).order_by('-created_at')

    serializer = TorrentSerializer(user_torrents, many=True)
    return Response({
        'user_torrents': serializer.data
    })


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_torrent(request, info_hash):
    """حذف تورنت (فقط توسط سازنده یا ادمین)"""

    torrent = get_object_or_404(Torrent, info_hash=info_hash)

    # بررسی دسترسی
    if torrent.created_by != request.user and not request.user.is_staff:
        return Response(
            {'error': 'Access denied'},
            status=status.HTTP_403_FORBIDDEN
        )

    # غیرفعال کردن تورنت (به جای حذف فیزیکی)
    torrent.is_active = False
    torrent.save()

    # لاگ حذف
    from logging_monitoring.models import SystemLog
    SystemLog.objects.create(
        category='admin',
        level='info',
        message=f'Torrent deleted: {torrent.name}',
        details={
            'torrent_id': torrent.id,
            'info_hash': torrent.info_hash,
            'deleted_by': request.user.username
        },
        user=request.user
    )

    return Response({
        'success': True,
        'message': f'Torrent {torrent.name} has been deleted'
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def torrent_peers(request, info_hash):
    """دریافت لیست peerهای یک تورنت"""

    torrent = get_object_or_404(Torrent, info_hash=info_hash, is_active=True)

    # فقط سازنده یا ادمین می‌توانند peerها را ببینند
    if torrent.created_by != request.user and not request.user.is_staff:
        return Response(
            {'error': 'Access denied'},
            status=status.HTTP_403_FORBIDDEN
        )

    # peerهای فعال (۲۴ ساعت گذشته)
    active_peers = Peer.objects.filter(
        torrent=torrent,
        last_announced__gte=timezone.now() - timezone.timedelta(hours=24)
    ).order_by('-last_announced')

    serializer = PeerSerializer(active_peers, many=True)
    return Response({
        'torrent': torrent.name,
        'active_peers': serializer.data
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def torrent_health(request, info_hash):
    """بررسی سلامت تورنت"""

    torrent = get_object_or_404(Torrent, info_hash=info_hash, is_active=True)

    try:
        stats = torrent.stats
        seeders = stats.seeders
        leechers = stats.leechers
    except TorrentStats.DoesNotExist:
        seeders = 0
        leechers = 0

    # محاسبه نسبت سلامت
    total_peers = seeders + leechers
    if total_peers == 0:
        health_score = 0
        health_status = 'dead'
    elif seeders >= leechers:
        health_score = min(100, (seeders / max(1, leechers)) * 50)
        health_status = 'excellent' if health_score >= 80 else 'good'
    else:
        health_score = max(0, 50 - (leechers / max(1, seeders)) * 25)
        health_status = 'poor' if health_score < 30 else 'fair'

    return Response({
        'torrent': torrent.name,
        'health_score': round(health_score, 1),
        'health_status': health_status,
        'seeders': seeders,
        'leechers': leechers,
        'total_peers': total_peers
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def download_torrent(request, info_hash):
    """دانلود فایل تورنت"""
    try:
        torrent = Torrent.objects.get(info_hash=info_hash, is_active=True)
    except Torrent.DoesNotExist:
        return Response({'error': 'Torrent not found'}, status=status.HTTP_404_NOT_FOUND)

    # Check access permissions for private torrents
    if torrent.is_private and request.user != torrent.created_by:
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    try:
        # Generate torrent file data
        torrent_data = generate_torrent_file(torrent)

        # Log the download
        if request.user.is_authenticated:
            from logging_monitoring.models import UserActivity
            UserActivity.objects.create(
                user=request.user,
                activity_type='torrent_download',
                description=f'Downloaded torrent: {torrent.name}',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={'torrent_id': torrent.id, 'info_hash': info_hash}
            )

        # Return torrent file
        from django.http import HttpResponse
        response = HttpResponse(torrent_data, content_type='application/x-bittorrent')
        response['Content-Disposition'] = f'attachment; filename="{torrent.name}.torrent"'
        return response

    except Exception as e:
        from logging_monitoring.models import SystemLog
        SystemLog.objects.create(
            category='tracker',
            level='error',
            message=f'Torrent download error: {str(e)}',
            user=request.user if request.user.is_authenticated else None,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={'torrent_id': torrent.id, 'error': str(e)}
        )

        return Response({'error': 'Download failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def generate_torrent_file(torrent):
    """Generate torrent file data from database"""
    import bencode
    from django.conf import settings

    # Build info dictionary
    info_dict = {
        'name': torrent.name.encode('utf-8'),
        'piece length': torrent.piece_length or 262144,  # Default 256KB
    }

    # Add pieces if available
    if torrent.pieces_hash:
        try:
            info_dict['pieces'] = bytes.fromhex(torrent.pieces_hash)
        except:
            pass

    # Add files information
    if torrent.files_count > 1:
        # Multi-file torrent (simplified - would need proper file structure)
        info_dict['files'] = [{
            'path': [torrent.name.encode('utf-8')],
            'length': torrent.size
        }]
    else:
        # Single file torrent
        info_dict['length'] = torrent.size

    # Add optional fields
    if torrent.comment:
        info_dict['comment'] = torrent.comment.encode('utf-8')

    if torrent.created_by_client:
        info_dict['created by'] = torrent.created_by_client.encode('utf-8')

    # Build main torrent dictionary
    torrent_dict = {
        'info': info_dict,
        'creation date': int(torrent.created_at.timestamp()),
    }

    # Add announce URL
    if torrent.announce_url:
        torrent_dict['announce'] = torrent.announce_url.encode('utf-8')
    else:
        # Use default tracker URL
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        torrent_dict['announce'] = f"{site_url}/announce".encode('utf-8')

    # Add comment
    if torrent.comment:
        torrent_dict['comment'] = torrent.comment.encode('utf-8')

    return bencode.encode(torrent_dict)