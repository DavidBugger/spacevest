from rest_framework import serializers
from .models import CustomUser, BankAccount, VirtualAccount

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'phone', 'country', 'wallet_balance', 'kyc_verified', 'role', 'created_at', 'updated_at']

class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ['id', 'user', 'account_name', 'account_number', 'bank_name', 'bank_code', 'is_primary', 'created_at', 'updated_at']

class VirtualAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = VirtualAccount
        fields = ['id', 'user', 'bank_name', 'account_number', 'account_name', 'provider_reference', 'is_active', 'created_at', 'updated_at']
