from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('refresh/', views.CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('invite/create/', views.create_invite_code, name='create_invite'),
]
