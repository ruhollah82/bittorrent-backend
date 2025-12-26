from django.urls import path
from . import views

app_name = 'torrents'

urlpatterns = [
    path('', views.TorrentListView.as_view(), name='list'),
    path('<str:info_hash>/', views.TorrentDetailView.as_view(), name='detail'),
    path('<str:info_hash>/stats/', views.TorrentStatsView.as_view(), name='stats'),
    path('<str:info_hash>/peers/', views.torrent_peers, name='peers'),
    path('<str:info_hash>/health/', views.torrent_health, name='health'),
    path('<str:info_hash>/delete/', views.delete_torrent, name='delete'),
    path('<str:info_hash>/download/', views.download_torrent, name='download'),
    path('upload/', views.upload_torrent, name='upload'),
    path('categories/', views.torrent_categories, name='categories'),
    path('popular/', views.torrent_popular, name='popular'),
    path('my-torrents/', views.user_torrents, name='user_torrents'),
]
