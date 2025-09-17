from django.urls import path
from . import views

urlpatterns = [
    path('rates/', views.CryptoRateListView.as_view(), name='crypto-rates'),
    path('supported/', views.SupportedCryptoListView.as_view(), name='supported-cryptos'),
    path('rates/<str:symbol>/', views.get_crypto_rate, name='crypto-rate-detail'),
    path('convert/', views.convert_crypto, name='convert-crypto'),
    path('quote/', views.get_purchase_quote, name='crypto-purchase-quote'),
    path('update-rates/', views.update_crypto_rates, name='update-crypto-rates'),
    path('admin/update-rate/', views.admin_update_rate, name='admin-update-rate'),
    path('admin/get-rates/', views.admin_get_rates, name='admin-get-rates'),
]
