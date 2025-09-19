from django.db import models
from .custom_user import CustomUser

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
        return f"{self.account_name} - {self.account_number} ({self.bank_name})"
