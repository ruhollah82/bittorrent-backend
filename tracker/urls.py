from django.urls import path
from . import views, views_new

app_name = 'tracker'

urlpatterns = [
    # New tracker implementation (recommended)
    path('announce', views_new.announce, name='announce'),
    path('scrape', views_new.scrape, name='scrape'),
    path('stats', views_new.stats, name='stats'),

    # Legacy views (for backward compatibility)
    # path('announce', views.announce, name='announce_old'),
    # path('scrape', views.scrape, name='scrape_old'),
]
