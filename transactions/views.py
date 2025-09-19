from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.db import transaction as db_transaction
from django.contrib.auth import get_user_model
import requests
from requests.adapters import HTTPAdapter
import uuid
import time
import random
from datetime import timedelta
from urllib3.util.retry import Retry
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

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_billers(request, category):
    """
    Fetch billers from Yanga API for the specified category (airtime or data_bundle)
    """
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {settings.YANGA_API_KEY}",
        "User-Agent": "SpaceVest/1.0 (https://spacevest.com.ng; support@spacevest.com.ng)",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://spacevest.com.ng"
    }

    # Map frontend category to Yanga API category
    api_category = 'data_bundle' if category == 'data_bundle' else category

    # Configure session with retry strategy
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    try:
        url = f"{settings.YANGA_API_BASE_URL}/bill-payments/billers/{api_category}"
        print(f"Making request to: {url}")  # Log the URL being called
        
        response = session.get(url, headers=headers, timeout=10)
        print(f"Response status: {response.status_code}")  # Log response status
        
        response.raise_for_status()  # Raise HTTPError for bad responses
        
        data = response.json()
        print(f"Yanga API response for {api_category}: {data}")  # Debug logging

        if not isinstance(data, dict):
            raise ValueError(f"Expected dict response, got {type(data).__name__}")
            
        if data.get('success'):
            billers_data = data.get('data', {})
            # Ensure billers_data has the expected structure
            if isinstance(billers_data, dict) and 'billers' in billers_data:
                billers_list = billers_data['billers']
            elif isinstance(billers_data, list):
                billers_list = billers_data
            else:
                billers_list = billers_data if billers_data else []

            # Use the actual biller codes from Yanga API response
            transformed_billers = []
            for biller in billers_list:
                if isinstance(biller, dict):
                    # Use the actual biller codes from Yanga API
                    biller_code = biller.get('code', '')
                    biller_name = biller.get('name', '')
                    has_products = biller.get('has_products', False)

                    transformed_billers.append({
                        'code': biller_code,
                        'name': biller_name,
                        'has_products': has_products,
                        'minimum': biller.get('minimum'),
                        'maximum': biller.get('maximum'),
                        'category': biller.get('category', api_category)
                    })

            return Response({'billers': transformed_billers}, status=status.HTTP_200_OK)
        else:
            error_msg = data.get('message', f'No billers found for this category ({response.status_code})')
            print(f"Yanga API error for {api_category}: {response.status_code} - {response.text}")
            return Response({'error': error_msg}, status=status.HTTP_404_NOT_FOUND)
    except requests.exceptions.RequestException as e:
        error_msg = f"Request error in get_billers for {api_category}: {str(e)}"
        print(error_msg)
        return Response({'error': 'Failed to fetch billers. Please try again later.', 'details': str(e)}, 
                       status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except ValueError as e:
        error_msg = f"Invalid response format in get_billers for {api_category}: {str(e)}"
        print(error_msg)
        return Response({'error': 'Invalid response from service provider', 'details': str(e)},
                       status=status.HTTP_502_BAD_GATEWAY)
    except Exception as e:
        error_msg = f"Unexpected error in get_billers for {api_category}: {str(e)}"
        print(error_msg)
        return Response({'error': 'An unexpected error occurred', 'details': str(e)},
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_products(request, biller_code):
    """
    Fetch products for a specific biller from Yanga API
    """
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {settings.YANGA_API_KEY}",
        "User-Agent": "SpaceVest/1.0 (https://spacevest.com.ng; support@spacevest.com.ng)",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://spacevest.com.ng"
    }

    # Use the actual biller codes from Yanga API
    api_biller_code = biller_code

    # Configure session with retry strategy
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    try:
        url = f"{settings.YANGA_API_BASE_URL}/bill-payments/products/{api_biller_code}"
        print(f"Making request to: {url}")  # Log the URL being called
        
        response = session.get(url, headers=headers, timeout=10)
        print(f"Response status: {response.status_code}")  # Log response status
        
        response.raise_for_status()  # Raise HTTPError for bad responses
        
        data = response.json()
        print(f"Yanga API products response for {api_biller_code}: {data}")

        if not isinstance(data, dict):
            raise ValueError(f"Expected dict response, got {type(data).__name__}")
            
        if data.get('success'):
            products_data = data.get('data', {})
            # Ensure products_data has the expected structure
            if isinstance(products_data, dict) and 'products' in products_data:
                products_list = products_data['products']
            elif isinstance(products_data, list):
                products_list = products_data
            else:
                products_list = products_data if products_data else []

            # Transform products to ensure consistent format
            transformed_products = []
            for product in products_list:
                if isinstance(product, dict):
                    transformed_products.append({
                        'code': product.get('code', ''),
                        'name': product.get('name', ''),
                        'amount': product.get('amount', 0),
                        'description': product.get('description', ''),
                        'validity': product.get('validity', ''),
                    })

            return Response({'products': transformed_products}, status=status.HTTP_200_OK)
        else:
            error_msg = data.get('message', f'Failed to fetch products from external API ({response.status_code})')
            print(f"Yanga API products error for {api_biller_code}: {response.status_code} - {response.text}")
            return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)
    except requests.exceptions.RequestException as e:
        error_msg = f"Request error in get_products for {api_biller_code}: {str(e)}"
        print(error_msg)  # Debug logging
        return Response({'error': 'Failed to fetch products. Please try again later.', 'details': str(e)}, 
                       status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except ValueError as e:
        error_msg = f"Invalid response format in get_products for {api_biller_code}: {str(e)}"
        print(error_msg)  # Debug logging
        return Response({'error': 'Invalid response from service provider', 'details': str(e)},
                       status=status.HTTP_502_BAD_GATEWAY)
    except Exception as e:
        error_msg = f"Unexpected error in get_products for {api_biller_code}: {str(e)}"
        print(error_msg)  # Debug logging
        return Response({'error': 'An unexpected error occurred', 'details': str(e)},
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def top_up(request):
    data = request.data
    top_up_type = data.get('type')

    # Add a small random delay to avoid appearing automated
    time.sleep(random.uniform(0.5, 1.5))



    print(f"Top-up request data: {data}")  # Debug logging

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {settings.YANGA_API_KEY}",
        "User-Agent": "SpaceVest/1.0 (https://spacevest.com.ng; support@spacevest.com.ng)"

    }

     # Configure retry strategy
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504, 429]
    )
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
    if top_up_type == 'airtime':
        serializer = AirtimePurchaseSerializer(data=data)
        print(f"Airtime serializer data: {data}")  # Debug logging
        print(f"Airtime serializer is_valid: {serializer.is_valid()}")  # Debug logging
        if not serializer.is_valid():
            print(f"Airtime serializer errors: {serializer.errors}")  # Debug logging
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            with db_transaction.atomic():
                validated_data = serializer.validated_data

                # Use the actual biller code from the network field
                api_biller_code = validated_data['network']

                # For airtime, check if biller has products
                products_url = f"{settings.YANGA_API_BASE_URL}/bill-payments/products/{api_biller_code}"
                products_response = requests.get(products_url, headers=headers)

                product_code = None
                if products_response.status_code == 200:
                    products_data = products_response.json()
                    if products_data.get('success') and products_data.get('data', {}).get('products'):
                        # Has predefined products - use product code
                        product_code = validated_data.get('product_code')
                        if not product_code:
                            return Response({'error': 'Product code is required for this airtime plan'}, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        # No predefined products - use amount directly
                        product_code = None
                else:
                    # Assume no products for airtime
                    product_code = None

                # Prepare payload for purchase
                import uuid
                request_id = str(uuid.uuid4())
                purchase_payload = {
                    "request_id": request_id,
                    "biller_code": api_biller_code,
                    "recipient": validated_data['phone_number'],
                    "sync": False
                }

                # Add product_code if available, otherwise add amount for custom airtime
                if product_code:
                    purchase_payload["product_code"] = product_code
                else:
                    # For custom airtime amount - convert to integer
                    purchase_payload["amount"] = int(validated_data['amount'])

                # Make purchase request
                purchase_url = f"{settings.YANGA_API_BASE_URL}/bill-payments/pay"
                print(f"Making purchase request to: {purchase_url}")  # Debug logging
                print(f"Purchase payload: {purchase_payload}")  # Debug logging
                purchase_response = requests.post(purchase_url, json=purchase_payload, headers=headers)
                print(f"Purchase response status: {purchase_response.status_code}")  # Debug logging
                print(f"Purchase response text: {purchase_response.text}")  # Debug logging

                if purchase_response.status_code != 200:
                    try:
                        error_data = purchase_response.json()
                        message = error_data.get('message', 'Failed to complete airtime purchase')
                        return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
                    except ValueError:
                        return Response({'error': 'Failed to complete airtime purchase'}, status=status.HTTP_400_BAD_REQUEST)
                    
                purchase_result = purchase_response.json()

                if not purchase_result.get('success'):
                    return Response({'error': purchase_result.get('message', 'Purchase failed')}, status=status.HTTP_400_BAD_REQUEST)

                # Create transaction
                transaction = Transaction.objects.create(
                    user=request.user,
                    transaction_type='debit',
                    category='airtime',
                    amount=validated_data['amount'],
                    description=f"Airtime purchase for {validated_data['phone_number']}",
                    metadata=purchase_result
                )

                # Create airtime details
                AirtimeTransaction.objects.create(
                    transaction=transaction,
                    phone_number=validated_data['phone_number'],
                    network=validated_data['network'],
                    plan_name=validated_data.get('plan_name')
                )

                # Deduct from wallet
                request.user.wallet_balance -= validated_data['amount']
                request.user.save()

                transaction.status = 'completed'
                transaction.save()

                return Response(TransactionSerializer(transaction).data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif top_up_type == 'data':
        plan = data.get('data_plan', '')
        amount = data.get('amount')
        product_code = data.get('product_code')
        network = data.get('network')

        # Ensure amount is properly handled
        if amount is None and plan:
            import re
            match = re.search(r'₦(\d+)', plan)
            if match:
                amount = int(match.group(1))

        data_copy = data.copy()
        data_copy['data_plan'] = plan
        data_copy['amount'] = amount

        serializer = DataPurchaseSerializer(data=data_copy)
        if serializer.is_valid():
            try:
                with db_transaction.atomic():
                    validated_data = serializer.validated_data

                    # Use the biller code from the network field (which is now the biller code)
                    biller_code = network

                    # For data bundles, product_code is always required since they have predefined products
                    if not product_code:
                        return Response({'error': 'Product code is required for data bundle purchase'}, status=status.HTTP_400_BAD_REQUEST)

                    final_product_code = product_code

                    # Prepare payload for purchase
                    import uuid
                    request_id = str(uuid.uuid4())
                    purchase_payload = {
                        "request_id": request_id,
                        "biller_code": biller_code,
                        "recipient": validated_data['phone_number'],
                        "sync": False,
                        "product_code": final_product_code
                    }

                    # Make purchase request
                    purchase_url = f"{settings.YANGA_API_BASE_URL}/bill-payments/pay"
                    purchase_response = requests.post(purchase_url, json=purchase_payload, headers=headers)
                    if purchase_response.status_code != 200:
                        return Response({'error': 'Failed to complete data bundle purchase'}, status=status.HTTP_502_BAD_GATEWAY)
                    purchase_result = purchase_response.json()

                    if not purchase_result.get('success'):
                        return Response({'error': purchase_result.get('message', 'Purchase failed')}, status=status.HTTP_400_BAD_REQUEST)

                    # Create transaction
                    transaction = Transaction.objects.create(
                        user=request.user,
                        transaction_type='debit',
                        category='data',
                        amount=validated_data['amount'],
                        description=f"Data purchase for {validated_data['phone_number']}",
                        metadata=purchase_result
                    )

                    # Create data details
                    DataTransaction.objects.create(
                        transaction=transaction,
                        phone_number=validated_data['phone_number'],
                        network=validated_data['network'],
                        data_plan=validated_data['data_plan'],
                        validity="30 days"  # Placeholder
                    )

                    # Deduct from wallet
                    request.user.wallet_balance -= validated_data['amount']
                    request.user.save()

                    transaction.status = 'completed'
                    transaction.save()

                    return Response(TransactionSerializer(transaction).data, status=status.HTTP_201_CREATED)

            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    else:
        return Response({'error': 'Invalid top-up type'}, status=status.HTTP_400_BAD_REQUEST)
