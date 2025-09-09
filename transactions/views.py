from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.db import transaction as db_transaction
from django.contrib.auth import get_user_model
from .models import Transaction, TransactionFee, CryptoTransaction, AirtimeTransaction, DataTransaction
from .serializers import (
    TransactionSerializer, CreateTransactionSerializer, TransferSerializer,
    WithdrawalSerializer, CryptoPurchaseSerializer, AirtimePurchaseSerializer,
    DataPurchaseSerializer
)
from users.models import BankAccount

User = get_user_model()

class TransactionListView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user).select_related(
            'fee', 'crypto_details', 'airtime_details', 'data_details'
        )

class TransactionDetailView(generics.RetrieveAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user).select_related(
            'fee', 'crypto_details', 'airtime_details', 'data_details'
        )

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def transfer_funds(request):
    serializer = TransferSerializer(data=request.data)
    if serializer.is_valid():
        try:
            with db_transaction.atomic():
                data = serializer.validated_data
                recipient = User.objects.get(email=data['recipient_email'])
                
                # Create transaction
                transaction = Transaction.objects.create(
                    user=request.user,
                    transaction_type='debit',
                    category='transfer',
                    amount=data['amount'],
                    description=data['description'],
                    recipient=recipient,
                    recipient_email=data['recipient_email']
                )
                
                # Deduct from sender
                request.user.wallet_balance -= data['amount']
                request.user.save()
                
                # Add to recipient
                recipient.wallet_balance += data['amount']
                recipient.save()
                
                # Update transaction status
                transaction.status = 'completed'
                transaction.save()
                
                return Response(TransactionSerializer(transaction).data, status=status.HTTP_201_CREATED)
                
        except User.DoesNotExist:
            return Response({'error': 'Recipient not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_funds(request):
    """
    Add funds to the user's wallet.
    """
    try:
        amount = request.data.get('amount')
        description = request.data.get('description', 'Wallet top-up')
        reference = request.data.get('reference')
        
        # Convert amount to Decimal if it's a string or float
        if isinstance(amount, (str, float)):
            try:
                from decimal import Decimal
                amount = Decimal(str(amount))
            except (ValueError, TypeError):
                return Response({'error': 'Invalid amount format. Must be a valid number.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if amount is None or amount <= 0:
            return Response({'error': 'Invalid amount specified. Amount must be greater than 0.'}, status=status.HTTP_400_BAD_REQUEST)

        with db_transaction.atomic():
            # Create transaction record
            transaction = Transaction.objects.create(
                user=request.user,
                transaction_type='credit',
                category='deposit',
                amount=amount,
                description=description,
                status='completed',
                reference=reference
            )
            
            # Update user's wallet balance
            request.user.wallet_balance += amount
            request.user.save()

            return Response(TransactionSerializer(transaction).data, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def withdraw_funds(request):
    serializer = WithdrawalSerializer(data=request.data)
    if serializer.is_valid():
        try:
            with db_transaction.atomic():
                data = serializer.validated_data
                bank_account = BankAccount.objects.get(id=data['bank_account_id'], user=request.user)
                
                # Create transaction
                transaction = Transaction.objects.create(
                    user=request.user,
                    transaction_type='debit',
                    category='withdrawal',
                    amount=data['amount'],
                    description=data.get('description', 'Withdrawal to bank account'),
                    bank_account=bank_account
                )
                
                # Deduct from wallet
                request.user.wallet_balance -= data['amount']
                request.user.save()
                
                # TODO: Integrate with Paystack or other payment gateway for actual bank transfer
                
                return Response({'message': 'Withdrawal request submitted', 'transaction': TransactionSerializer(transaction).data}, status=status.HTTP_201_CREATED)
                
        except BankAccount.DoesNotExist:
            return Response({'error': 'Bank account not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def purchase_crypto(request):
    serializer = CryptoPurchaseSerializer(data=request.data)
    if serializer.is_valid():
        try:
            with db_transaction.atomic():
                data = serializer.validated_data
                
                # TODO: Get current exchange rate from CoinGecko API
                exchange_rate = 1500.00  # Placeholder - replace with actual API call
                crypto_amount = data['amount_ngn'] / exchange_rate
                
                # Create transaction
                transaction = Transaction.objects.create(
                    user=request.user,
                    transaction_type='debit',
                    category='crypto_buy',
                    amount=data['amount_ngn'],
                    description=f"Purchase {data['cryptocurrency']}",
                    metadata={'exchange_rate': float(exchange_rate)}
                )
                
                # Create crypto details
                CryptoTransaction.objects.create(
                    transaction=transaction,
                    cryptocurrency=data['cryptocurrency'],
                    amount_crypto=crypto_amount,
                    exchange_rate=exchange_rate,
                    wallet_address=data.get('wallet_address'),
                    network=data.get('network')
                )
                
                # Deduct from wallet
                request.user.wallet_balance -= data['amount_ngn']
                request.user.save()
                
                transaction.status = 'completed'
                transaction.save()
                
                return Response(TransactionSerializer(transaction).data, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def purchase_airtime(request):
    serializer = AirtimePurchaseSerializer(data=request.data)
    if serializer.is_valid():
        try:
            with db_transaction.atomic():
                data = serializer.validated_data
                
                # Create transaction
                transaction = Transaction.objects.create(
                    user=request.user,
                    transaction_type='debit',
                    category='airtime',
                    amount=data['amount'],
                    description=f"Airtime purchase for {data['phone_number']}"
                )
                
                # Create airtime details
                AirtimeTransaction.objects.create(
                    transaction=transaction,
                    phone_number=data['phone_number'],
                    network=data['network'],
                    plan_name=data.get('plan_name')
                )
                
                # Deduct from wallet
                request.user.wallet_balance -= data['amount']
                request.user.save()
                
                # TODO: Integrate with airtime API
                
                transaction.status = 'completed'
                transaction.save()
                
                return Response(TransactionSerializer(transaction).data, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def purchase_data(request):
    serializer = DataPurchaseSerializer(data=request.data)
    if serializer.is_valid():
        try:
            with db_transaction.atomic():
                data = serializer.validated_data
                
                # Create transaction
                transaction = Transaction.objects.create(
                    user=request.user,
                    transaction_type='debit',
                    category='data',
                    amount=data['amount'],
                    description=f"Data purchase for {data['phone_number']}"
                )
                
                # Create data details
                DataTransaction.objects.create(
                    transaction=transaction,
                    phone_number=data['phone_number'],
                    network=data['network'],
                    data_plan=data['data_plan'],
                    validity="30 days"  # Placeholder
                )
                
                # Deduct from wallet
                request.user.wallet_balance -= data['amount']
                request.user.save()
                
                # TODO: Integrate with data API
                
                transaction.status = 'completed'
                transaction.save()
                
                return Response(TransactionSerializer(transaction).data, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
