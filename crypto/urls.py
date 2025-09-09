from django.urls import path
from . import views

urlpatterns = [
    path('rates/', views.CryptoRateListView.as_view(), name='crypto-rates'),
    path('supported/', views.SupportedCryptoListView.as_view(), name='supported-cryptos'),
    path('rates/<str:symbol>/', views.get_crypto_rate, name='crypto-rate-detail'),
    path('convert/', views.convert_crypto, name='convert-crypto'),
    path('quote/', views.get_purchase_quote, name='crypto-purchase-quote'),
    path('update-rates/', views.update_crypto_rates, name='update-crypto-rates'),
]
