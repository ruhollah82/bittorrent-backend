from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('dashboard/', views.AdminDashboardView.as_view(), name='dashboard'),
    path('users/', views.UserManagementListView.as_view(), name='users_list'),
    path('users/<int:pk>/', views.UserManagementDetailView.as_view(), name='user_detail'),
    path('invite-codes/', views.InviteCodeManagementListView.as_view(), name='invite_codes'),
    path('system-config/', views.SystemConfigListView.as_view(), name='system_config'),
    path('system-config/<int:pk>/', views.SystemConfigDetailView.as_view(), name='system_config_detail'),
    path('reports/generate/', views.generate_report, name='generate_report'),
    path('mass-action/', views.mass_user_action, name='mass_user_action'),
    path('actions-log/', views.admin_actions_log, name='actions_log'),
    path('maintenance/', views.system_maintenance, name='maintenance'),
    path('analytics/', views.advanced_analytics, name='advanced_analytics'),
    path('bulk-torrent-moderation/', views.bulk_torrent_moderation, name='bulk_torrent_moderation'),
    path('cleanup/', views.system_cleanup, name='system_cleanup'),
    path('performance-metrics/', views.system_performance_metrics, name='performance_metrics'),
]