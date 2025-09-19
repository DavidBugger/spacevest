from django.db import models
from .custom_user import CustomUser

class BankAccount(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bank_accounts')
    account_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=255)
    bank_code = models.CharField(max_length=10)
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.account_name} - {self.account_number} ({self.bank_name})"
