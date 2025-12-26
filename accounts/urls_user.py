from django.urls import path
from . import views

app_name = 'accounts_user'

urlpatterns = [
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('stats/', views.UserStatsView.as_view(), name='stats'),
    path('tokens/', views.AuthTokenListView.as_view(), name='tokens'),
    path('tokens/<int:pk>/', views.AuthTokenDetailView.as_view(), name='token_detail'),
]
