from django.urls import path
from . import views

urlpatterns = [
    path('', views.TransactionListView.as_view(), name='transaction-list'),
    path('<int:pk>/', views.TransactionDetailView.as_view(), name='transaction-detail'),
    path('transfer/', views.transfer_funds, name='transfer-funds'),
    path('withdraw/', views.withdraw_funds, name='withdraw-funds'),
    path('purchase/crypto/', views.purchase_crypto, name='purchase-crypto'),
    path('purchase/airtime/', views.purchase_airtime, name='purchase-airtime'),
    path('purchase/data/', views.purchase_data, name='purchase-data'),
    path('add-funds/', views.add_funds, name='add-funds'),  # New endpoint for adding funds
]
