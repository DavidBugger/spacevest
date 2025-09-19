from rest_framework import serializers
from django.conf import settings
from .models import Bank, BankAccountVerification, VirtualAccountRequest

class BankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bank
        fields = ['id', 'name', 'code', 'country', 'currency', 'type', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class PaystackBankSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False)
    slug = serializers.CharField(required=False)
    code = serializers.CharField(required=True)
    longcode = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    gateway = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    pay_with_bank = serializers.BooleanField(required=False, default=False)
    supports_transfer = serializers.BooleanField(required=False, default=False)
    active = serializers.BooleanField(required=False, default=True)
    country = serializers.CharField(required=False, default='Nigeria')
    currency = serializers.CharField(required=False, default='NGN')
    type = serializers.CharField(required=False, default='nuban')
    is_deleted = serializers.BooleanField(required=False, default=False)
    created_at = serializers.DateTimeField(required=False, allow_null=True)
    updated_at = serializers.DateTimeField(required=False, allow_null=True)

class BankAccountVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccountVerification
        fields = [
            'id', 'account_number', 'bank_code', 'account_name', 'status',
            'verification_reference', 'created_at', 'updated_at'
        ]
        read_only_fields = ['account_name', 'status', 'verification_reference', 'created_at', 'updated_at']

class VirtualAccountRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = VirtualAccountRequest
        fields = [
            'id', 'provider', 'account_number', 'account_name', 'bank_name',
            'provider_reference', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['account_number', 'account_name', 'bank_name', 'provider_reference', 'status', 'created_at', 'updated_at']

class VerifyAccountSerializer(serializers.Serializer):
    account_number = serializers.CharField(max_length=20)
    bank_code = serializers.CharField(max_length=10)

class CreateVirtualAccountSerializer(serializers.Serializer):
    provider_id = serializers.IntegerField()

class WebhookSerializer(serializers.Serializer):
    event = serializers.CharField(max_length=100)
    data = serializers.JSONField()
    signature = serializers.CharField(max_length=255, required=False)

class BankAccountSerializer(serializers.ModelSerializer):
    bank_name = serializers.CharField(source='bank.name', read_only=True)
    bank_code = serializers.CharField(write_only=True)
    
    class Meta:
        model = BankAccountVerification
        fields = [
            'id', 'account_number', 'bank_code', 'bank_name', 
            'account_name', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['account_name', 'status', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        user = self.context['request'].user
        bank_code = validated_data.pop('bank_code')
        
        # Get or create bank
        bank = Bank.objects.get(code=bank_code)
        
        # Create bank account verification
        account = BankAccountVerification.objects.create(
            user=user,
            bank=bank,
            **validated_data,
            status='verified'  # Assuming it's verified since we're using the verify-account endpoint first
        )
        
        return account
