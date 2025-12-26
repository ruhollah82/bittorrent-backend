from django.urls import path, include

app_name = 'api'

urlpatterns = [
    path('auth/', include('accounts.urls')),
    path('user/', include('accounts.urls_user')),
    path('torrents/', include('torrents.urls')),
    path('credits/', include('credits.urls')),
    path('security/', include('security.urls')),
    path('logs/', include('logging_monitoring.urls')),
    path('admin/', include('admin_panel.urls')),
]
