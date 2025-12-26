from django.urls import path
from . import views

app_name = 'logging_monitoring'

urlpatterns = [
    path('system-logs/', views.SystemLogListView.as_view(), name='system_logs'),
    path('user-activities/', views.UserActivityListView.as_view(), name='user_activities'),
    path('alerts/', views.AlertListView.as_view(), name='alerts'),
    path('alerts/<int:pk>/', views.AlertDetailView.as_view(), name='alert_detail'),
    path('system-stats/', views.SystemStatsListView.as_view(), name='system_stats'),
    path('dashboard/', views.dashboard_stats, name='dashboard'),
    path('analyze/', views.analyze_logs, name='analyze_logs'),
    path('alerts/create/', views.create_manual_alert, name='create_alert'),
    path('health/', views.system_health_check, name='health_check'),
]
