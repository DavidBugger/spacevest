from rest_framework import serializers
from .models import CryptoRate, CryptoPriceHistory, SupportedCrypto

class CryptoRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CryptoRate
        fields = [
            'id', 'cryptocurrency', 'symbol', 'current_price_ngn', 'current_price_usd',
            'market_cap', 'volume_24h', 'price_change_24h', 'price_change_percentage_24h',
            'last_updated'
        ]

class CryptoPriceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CryptoPriceHistory
        fields = ['id', 'crypto_rate', 'price_ngn', 'price_usd', 'timestamp']

class SupportedCryptoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportedCrypto
        fields = [
            'id', 'name', 'symbol', 'is_active', 'min_purchase_amount',
            'max_purchase_amount', 'network_fee', 'description', 'icon_url'
        ]

class CryptoConversionSerializer(serializers.Serializer):
    cryptocurrency = serializers.CharField(max_length=50)
    amount = serializers.DecimalField(max_digits=20, decimal_places=8)
    to_currency = serializers.ChoiceField(choices=[('NGN', 'Naira'), ('USD', 'US Dollar')])

class CryptoPurchaseQuoteSerializer(serializers.Serializer):
    cryptocurrency = serializers.CharField(max_length=50)
    amount_ngn = serializers.DecimalField(max_digits=15, decimal_places=2)
    include_fees = serializers.BooleanField(default=True)
