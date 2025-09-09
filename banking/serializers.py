from rest_framework import serializers
from .models import Bank, BankAccountVerification, VirtualAccountRequest

class BankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bank
        fields = ['id', 'name', 'code', 'country', 'is_active', 'created_at']

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
