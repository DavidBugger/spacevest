from rest_framework import serializers
from .models import Transaction, TransactionFee, CryptoTransaction, AirtimeTransaction, DataTransaction

class TransactionFeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionFee
        fields = ['id', 'amount', 'description', 'created_at']

class CryptoTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CryptoTransaction
        fields = ['id', 'cryptocurrency', 'amount_crypto', 'exchange_rate', 'wallet_address', 'network']

class AirtimeTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirtimeTransaction
        fields = ['id', 'phone_number', 'network', 'plan_name']

class DataTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataTransaction
        fields = ['id', 'phone_number', 'network', 'data_plan', 'validity']

class TransactionSerializer(serializers.ModelSerializer):
    fee = TransactionFeeSerializer(read_only=True)
    crypto_details = CryptoTransactionSerializer(read_only=True)
    airtime_details = AirtimeTransactionSerializer(read_only=True)
    data_details = DataTransactionSerializer(read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'transaction_type', 'category', 'amount', 'status', 'description',
            'reference', 'metadata', 'recipient', 'recipient_email', 'bank_account',
            'created_at', 'updated_at', 'completed_at', 'fee', 'crypto_details',
            'airtime_details', 'data_details'
        ]
        read_only_fields = ['reference', 'created_at', 'updated_at', 'completed_at']

class CreateTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['transaction_type', 'category', 'amount', 'description', 'recipient_email', 'metadata']

class TransferSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    recipient_email = serializers.EmailField()
    description = serializers.CharField(max_length=500)

class WithdrawalSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    bank_account_id = serializers.IntegerField()
    description = serializers.CharField(max_length=500, required=False)

class CryptoPurchaseSerializer(serializers.Serializer):
    cryptocurrency = serializers.CharField(max_length=50)
    amount_ngn = serializers.DecimalField(max_digits=15, decimal_places=2)
    wallet_address = serializers.CharField(max_length=255, required=False)
    network = serializers.CharField(max_length=50, required=False)

class AirtimePurchaseSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    network = serializers.CharField(max_length=50)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    plan_name = serializers.CharField(max_length=100, required=False)
    product_code = serializers.CharField(max_length=100, required=False, allow_blank=True)

class DataPurchaseSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    network = serializers.CharField(max_length=50)
    data_plan = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
