from django.urls import path
from . import views

app_name = 'credits'

urlpatterns = [
    path('balance/', views.CreditBalanceView.as_view(), name='balance'),
    path('transactions/', views.CreditTransactionListView.as_view(), name='transactions'),
    path('transactions/<int:pk>/', views.CreditTransactionDetailView.as_view(), name='transaction_detail'),
    path('user-classes/', views.user_class_info, name='user_classes'),
    path('check-download/', views.check_download_permission, name='check_download'),
    path('lock-credit/', views.lock_credit_for_download, name='lock_credit'),
    path('complete-download/', views.complete_download_transaction, name='complete_download'),
    path('upload-credit/', views.calculate_upload_credit, name='upload_credit'),
    path('ratio-status/', views.check_ratio_status, name='ratio_status'),
    # Admin endpoints
    path('admin/adjust/', views.adjust_user_credit, name='admin_adjust'),
    path('admin/promote/', views.promote_user_class, name='admin_promote'),
]
