from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta

from security.models import AnnounceLog
from torrents.models import Torrent, Peer, TorrentStats


@admin.register(AnnounceLog)
class AnnounceLogAdmin(admin.ModelAdmin):
    """Admin interface for tracker announce logs"""

    list_display = ('user', 'torrent', 'event', 'uploaded', 'downloaded', 'timestamp', 'ip_address', 'is_suspicious')
    list_filter = ('event', 'timestamp', 'is_suspicious', 'torrent__name')
    search_fields = ('user__username', 'torrent__name', 'ip_address', 'peer_id')
    readonly_fields = ('id', 'timestamp', 'user_link', 'torrent_link')
    date_hierarchy = 'timestamp'

    fieldsets = (
        ('Basic Info', {
            'fields': ('user_link', 'torrent_link', 'event', 'timestamp')
        }),
        ('Transfer Stats', {
            'fields': ('uploaded', 'downloaded', 'left')
        }),
        ('Connection Info', {
            'fields': ('ip_address', 'port', 'peer_id', 'user_agent')
        }),
        ('Security', {
            'fields': ('is_suspicious', 'suspicious_reason')
        }),
    )

    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:accounts_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return '-'
    user_link.short_description = 'User'

    def torrent_link(self, obj):
        if obj.torrent:
            url = reverse('admin:torrents_torrent_change', args=[obj.torrent.id])
            return format_html('<a href="{}">{}</a>', url, obj.torrent.name)
        return '-'
    torrent_link.short_description = 'Torrent'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class PeerInline(admin.TabularInline):
    """Inline admin for peers in torrent admin"""
    model = Peer
    extra = 0
    readonly_fields = ('user', 'peer_id', 'ip_address', 'port', 'uploaded', 'downloaded', 'state', 'last_announced')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(TorrentStats)
class TorrentStatsAdmin(admin.ModelAdmin):
    """Admin interface for torrent statistics"""

    list_display = ('torrent', 'seeders', 'leechers', 'completed', 'last_updated')
    list_filter = ('last_updated',)
    search_fields = ('torrent__name', 'torrent__info_hash')
    readonly_fields = ('torrent', 'seeders', 'leechers', 'completed', 'last_updated')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# Custom admin views for tracker monitoring
class TrackerAdminSite(admin.AdminSite):
    """Custom admin site for tracker monitoring"""

    site_header = 'BitTorrent Tracker Administration'
    site_title = 'Tracker Admin'
    index_title = 'Tracker Monitoring Dashboard'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('tracker-dashboard/', self.admin_view(self.tracker_dashboard), name='tracker_dashboard'),
        ]
        return custom_urls + urls

    def tracker_dashboard(self, request):
        """Tracker monitoring dashboard"""
        context = {
            'title': 'Tracker Dashboard',
            'opts': self._registry.get(Torrent)._meta if Torrent in self._registry else None,
        }

        # Recent activity
        last_hour = timezone.now() - timedelta(hours=1)
        context['recent_announces'] = AnnounceLog.objects.filter(timestamp__gte=last_hour).count()
        context['active_peers'] = Peer.objects.filter(last_announced__gte=last_hour).count()
        context['active_torrents'] = Torrent.objects.filter(peers__last_announced__gte=last_hour).distinct().count()

        # Top torrents by activity
        context['top_torrents'] = Torrent.objects.annotate(
            recent_announces=Count('announcelog', filter=AnnounceLog.objects.filter(timestamp__gte=last_hour))
        ).filter(recent_announces__gt=0).order_by('-recent_announces')[:10]

        # System health
        context['total_torrents'] = Torrent.objects.count()
        context['total_users'] = AnnounceLog.objects.values('user').distinct().count()

        return self.render(request, 'admin/tracker_dashboard.html', context)


# Create tracker admin site instance
tracker_admin = TrackerAdminSite(name='tracker_admin')
