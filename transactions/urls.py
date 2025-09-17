from django.urls import path
from . import views

urlpatterns = [
    path('', views.TransactionListView.as_view(), name='transaction-list'),
    path('history/', views.TransactionListView.as_view(), name='transaction-history'),
    path('<int:pk>/', views.TransactionDetailView.as_view(), name='transaction-detail'),
    path('transfer/', views.transfer_funds, name='transfer-funds'),
    path('withdraw/', views.withdraw_funds, name='withdraw-funds'),
    path('purchase/crypto/', views.purchase_crypto, name='purchase-crypto'),
    path('purchase/airtime/', views.purchase_airtime, name='purchase-airtime'),
    path('purchase/data/', views.purchase_data, name='purchase-data'),
    path('top-up/', views.top_up, name='top-up'),
    path('add-funds/', views.add_funds, name='add-funds'),  # New endpoint for adding funds
    path('billers/<str:category>/', views.get_billers, name='get-billers'),
    path('products/<str:biller_code>/', views.get_products, name='get-products'),
]
