from django.db import models

class CryptoRate(models.Model):
    cryptocurrency = models.CharField(max_length=50, unique=True)  # BTC, ETH, USDT, etc.
    symbol = models.CharField(max_length=10)  # BTC, ETH, USDT
    current_price_ngn = models.DecimalField(max_digits=15, decimal_places=2)
    current_price_usd = models.DecimalField(max_digits=15, decimal_places=2)
    market_cap = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    volume_24h = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    price_change_24h = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_change_percentage_24h = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    last_updated = models.DateTimeField()
    
    class Meta:
        ordering = ['cryptocurrency']
    
    def __str__(self):
        return f"{self.cryptocurrency} - ₦{self.current_price_ngn}"

class CryptoPriceHistory(models.Model):
    crypto_rate = models.ForeignKey(CryptoRate, on_delete=models.CASCADE, related_name='price_history')
    price_ngn = models.DecimalField(max_digits=15, decimal_places=2)
    price_usd = models.DecimalField(max_digits=15, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['crypto_rate', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.crypto_rate.cryptocurrency} - ₦{self.price_ngn} at {self.timestamp}"

class SupportedCrypto(models.Model):
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10, unique=True)
    is_active = models.BooleanField(default=True)
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, default=1000.00)
    max_purchase_amount = models.DecimalField(max_digits=15, decimal_places=2, default=1000000.00)
    network_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    description = models.TextField(blank=True)
    icon_url = models.URLField(blank=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.symbol})"
