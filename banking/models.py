from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Bank(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=10, unique=True)
    country = models.CharField(max_length=100, default='Nigeria')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"

class BankAccountVerification(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bank_verifications')
    account_number = models.CharField(max_length=20)
    bank_code = models.CharField(max_length=10)
    account_name = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    verification_reference = models.CharField(max_length=255, blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'account_number', 'bank_code']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.account_number} - {self.status}"

class VirtualAccountProvider(models.Model):
    name = models.CharField(max_length=255)
    api_key = models.CharField(max_length=255)
    secret_key = models.CharField(max_length=255)
    base_url = models.URLField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class VirtualAccountRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('created', 'Created'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='virtual_account_requests')
    provider = models.ForeignKey(VirtualAccountProvider, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=20, blank=True, null=True)
    account_name = models.CharField(max_length=255, blank=True, null=True)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    provider_reference = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.status}"

class WebhookEvent(models.Model):
    EVENT_TYPES = [
        ('transfer', 'Transfer'),
        ('virtual_account', 'Virtual Account'),
        ('verification', 'Verification'),
    ]
    
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    provider = models.CharField(max_length=100)
    payload = models.JSONField()
    signature = models.CharField(max_length=255, blank=True, null=True)
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.event_type} - {self.provider} - {self.created_at}"
