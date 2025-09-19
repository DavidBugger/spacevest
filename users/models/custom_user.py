from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils.translation import gettext_lazy as _

class CustomUser(AbstractUser):
    """Custom user model that supports using email instead of username"""
    objects = UserManager()
    
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
