from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]
    
    TRANSACTION_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    TRANSACTION_CATEGORIES = [
        ('transfer', 'Transfer'),
        ('withdrawal', 'Withdrawal'),
        ('deposit', 'Deposit'),
        ('airtime', 'Airtime Purchase'),
        ('data', 'Data Purchase'),
        ('cable_tv', 'Cable TV'),
        ('crypto_sell', 'Crypto Sale'),
        ('crypto_buy', 'Crypto Purchase'),
        ('bill_payment', 'Bill Payment'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    category = models.CharField(max_length=20, choices=TRANSACTION_CATEGORIES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=10, choices=TRANSACTION_STATUS, default='pending')
    description = models.TextField()
    reference = models.CharField(max_length=255, unique=True, blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # For transfers
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_transactions')
    recipient_email = models.EmailField(blank=True, null=True)
    
    # For bank transactions
    bank_account = models.ForeignKey('users.BankAccount', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['reference']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} - {self.amount} - {self.status}"
    
    def save(self, *args, **kwargs):
        if not self.reference:
            # Generate a unique reference if not provided
            import uuid
            self.reference = f"TX{str(uuid.uuid4()).replace('-', '').upper()[:12]}"
        super().save(*args, **kwargs)

class TransactionFee(models.Model):
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name='fee')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Fee for {self.transaction.reference}: {self.amount}"

class CryptoTransaction(models.Model):
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name='crypto_details')
    cryptocurrency = models.CharField(max_length=50)  # BTC, ETH, USDT, etc.
    amount_crypto = models.DecimalField(max_digits=20, decimal_places=8)
    exchange_rate = models.DecimalField(max_digits=15, decimal_places=2)
    wallet_address = models.CharField(max_length=255, blank=True, null=True)
    network = models.CharField(max_length=50, blank=True, null=True)
    
    def __str__(self):
        return f"{self.cryptocurrency} - {self.amount_crypto}"

class AirtimeTransaction(models.Model):
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name='airtime_details')
    phone_number = models.CharField(max_length=15)
    network = models.CharField(max_length=50)
    plan_name = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return f"{self.network} - {self.phone_number}"

class DataTransaction(models.Model):
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name='data_details')
    phone_number = models.CharField(max_length=15)
    network = models.CharField(max_length=50)
    data_plan = models.CharField(max_length=100)
    validity = models.CharField(max_length=50, blank=True, null=True)
    
    def __str__(self):
        return f"{self.network} - {self.data_plan}"
