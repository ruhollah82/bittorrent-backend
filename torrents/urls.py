from django.urls import path, re_path
from . import views

app_name = 'torrents'

urlpatterns = [
    path('', views.TorrentListView.as_view(), name='list'),
    re_path(r'^(?P<info_hash>[a-fA-F0-9]{40})/$', views.TorrentDetailView.as_view(), name='detail'),
    re_path(r'^(?P<info_hash>[a-fA-F0-9]{40})/stats/$', views.TorrentStatsView.as_view(), name='stats'),
    re_path(r'^(?P<info_hash>[a-fA-F0-9]{40})/peers/$', views.torrent_peers, name='peers'),
    re_path(r'^(?P<info_hash>[a-fA-F0-9]{40})/health/$', views.torrent_health, name='health'),
    re_path(r'^(?P<info_hash>[a-fA-F0-9]{40})/delete/$', views.delete_torrent, name='delete'),
    re_path(r'^(?P<info_hash>[a-fA-F0-9]{40})/download/$', views.download_torrent, name='download'),
    path('upload/', views.upload_torrent, name='upload'),
    path('categories/', views.torrent_categories, name='categories'),
    path('categories/list/', views.categories_list, name='categories_list'),
    path('popular/', views.torrent_popular, name='popular'),
    path('my-torrents/', views.user_torrents, name='user_torrents'),
]
