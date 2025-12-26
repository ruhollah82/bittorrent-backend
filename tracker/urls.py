from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    path('announce', views.announce, name='announce'),
    path('scrape', views.scrape, name='scrape'),
]
