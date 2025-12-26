from django.urls import path
from . import views

app_name = 'security'

urlpatterns = [
    path('suspicious-activities/', views.SuspiciousActivityListView.as_view(), name='suspicious_list'),
    path('suspicious-activities/<int:pk>/', views.SuspiciousActivityDetailView.as_view(), name='suspicious_detail'),
    path('announce-logs/', views.AnnounceLogListView.as_view(), name='announce_logs'),
    path('ip-blocks/', views.IPBlockListView.as_view(), name='ip_blocks'),
    path('ip-blocks/<int:pk>/', views.IPBlockDetailView.as_view(), name='ip_block_detail'),
    path('stats/', views.security_stats, name='security_stats'),
    path('analyze-user/', views.analyze_user_behavior, name='analyze_user'),
    path('ban-user/', views.ban_user, name='ban_user'),
    path('unban-user/', views.unban_user, name='unban_user'),
    path('clear-rate-limits/', views.clear_rate_limits, name='clear_rate_limits'),
]
