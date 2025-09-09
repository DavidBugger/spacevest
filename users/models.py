from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class CustomUser(AbstractUser):
    # Basic user information
    phone = models.CharField(max_length=15, blank=True, null=True)
    country = models.CharField(max_length=100, default='Nigeria')
    
    # Wallet and financial information
    wallet_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    
    # KYC verification
    kyc_verified = models.BooleanField(default=False)
    kyc_details = models.JSONField(default=dict, blank=True)
    
    # Security settings
    security_settings = models.JSONField(default=dict, blank=True)
    
    # Preferences
    preferences = models.JSONField(default=dict, blank=True)
    
    # Points and rewards
    points = models.IntegerField(default=0)
    
    # Role-based access
    ROLE_CHOICES = [
        ('user', 'User'),
        ('admin', 'Admin'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
    
    def __str__(self):
        return self.email or self.username

class BankAccount(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bank_accounts')
    account_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=255)
    bank_code = models.CharField(max_length=10)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'account_number']
    
    def __str__(self):
        return f"{self.account_name} - {self.bank_name} ({self.account_number})"

class VirtualAccount(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='virtual_account')
    bank_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=20)
    account_name = models.CharField(max_length=255)
    provider_reference = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.account_name} - {self.bank_name} ({self.account_number})"
