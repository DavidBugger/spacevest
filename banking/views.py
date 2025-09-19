from rest_framework import generics, status, mixins
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
import requests
from decouple import config
from django.db import transaction as db_transaction
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from .models import Bank, BankAccountVerification, VirtualAccountProvider, VirtualAccountRequest
from .serializers import (
    BankSerializer, BankAccountVerificationSerializer, VirtualAccountRequestSerializer,
    VerifyAccountSerializer, CreateVirtualAccountSerializer, PaystackBankSerializer, BankAccountSerializer
)
from users.models import BankAccount

PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY')
PAYSTACK_BASE_URL = 'https://api.paystack.co'

class BankListView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        use_cache = request.query_params.get('cache', 'true').lower() == 'true'
        
        # Try to get banks from cache if enabled
        if use_cache:
            cached_banks = cache.get('paystack_banks_list')
            if cached_banks:
                return Response(cached_banks)
        
        try:
            # Fetch from Paystack
            headers = {
                'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{PAYSTACK_BASE_URL}/bank",
                params={'country': 'Nigeria'},
                headers=headers,
                timeout=10  # 10 seconds timeout
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if not response_data.get('status'):
                    raise Exception(response_data.get('message', 'Invalid response from Paystack'))
                
                paystack_banks = response_data.get('data', [])
                
                # Cache the raw result for 24 hours
                cache.set('paystack_banks_list', paystack_banks, 60 * 60 * 24)
                
                # Update local database for reference
                for bank_data in paystack_banks:
                    # Ensure required fields have defaults
                    bank_data.setdefault('country', 'Nigeria')
                    bank_data.setdefault('currency', 'NGN')
                    bank_data.setdefault('type', 'nuban')
                    bank_data.setdefault('active', True)
                    Bank.objects.update_or_create(
                        code=bank_data['code'],
                        defaults={
                            'name': bank_data['name'],
                            'country': bank_data.get('country', 'Nigeria'),
                            'currency': bank_data.get('currency', 'NGN'),
                            'type': bank_data.get('type', 'nuban'),
                            'is_active': bank_data.get('active', True)
                        }
                    )
                
                return Response({
                    'status': True,
                    'message': 'Banks retrieved successfully',
                    'data': paystack_banks
                })
            
            error_message = f'Paystack API error: {response.status_code} - {response.text}'
            return Response(
                {'status': False, 'message': error_message},
                status=status.HTTP_502_BAD_GATEWAY
            )
                
        except requests.Timeout:
            error_message = 'Request to Paystack API timed out'
        except requests.RequestException as e:
            error_message = f'Error connecting to Paystack: {str(e)}'
        except Exception as e:
            error_message = f'Error processing bank list: {str(e)}'
        
        # Fallback to local database if Paystack is down or error occurred
        local_banks = Bank.objects.filter(is_active=True).order_by('name')
        if local_banks.exists():
            serializer = BankSerializer(local_banks, many=True)
            return Response({
                'status': True,
                'message': 'Using cached bank data',
                'data': serializer.data,
                'cached': True
            })
        
        return Response(
            {'status': False, 'message': error_message},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

class BankAccountVerificationListView(generics.ListAPIView):
    serializer_class = BankAccountVerificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BankAccountVerification.objects.filter(user=self.request.user)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_bank_account(request):
    """
    Verify a bank account using Paystack's API.
    
    Request body should contain:
    - account_number: The bank account number to verify
    - bank_code: The bank code from the list of supported banks
    
    Returns:
    - 200: Account verified successfully
    - 400: Invalid input or verification failed
    - 409: Account already verified
    - 500: Server error
    """
    serializer = VerifyAccountSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'status': False, 'message': 'Validation error', 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    data = serializer.validated_data
    account_number = data['account_number'].strip()
    # bank_code = data['bank_code'].strip()
    bank_code = '001'
    
    try:
        with db_transaction.atomic():
            # Check for any existing verification (regardless of status)
            existing_verification = BankAccountVerification.objects.filter(
                user=request.user,
                account_number=account_number,
                bank_code=bank_code
            ).select_for_update().first()
            
            if existing_verification and existing_verification.status == 'verified':
                return Response(
                    {
                        'status': True,
                        'message': 'Account already verified',
                        'data': BankAccountVerificationSerializer(existing_verification).data
                    },
                    status=status.HTTP_409_CONFLICT
                )
            # If pending or failed, we'll update the existing record instead of creating a new one
        
        # Call Paystack API for verification
        headers = {
            'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(
                f"{PAYSTACK_BASE_URL}/bank/resolve",
                params={
                    'account_number': account_number,
                    'bank_code': bank_code
                },
                headers=headers,
                timeout=10  # 10 seconds timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            if not result.get('status') or 'data' not in result:
                raise Exception(result.get('message', 'Invalid response from Paystack'))
            
            # Get bank name for the account
            bank_name = get_bank_name(bank_code)
            if not bank_name:
                bank_name = f"Bank ({bank_code})"
            
            with db_transaction.atomic():
                # Update existing verification or create a new one
                verification_data = {
                    'account_name': result['data']['account_name'],
                    'status': 'verified',
                    'verification_reference': result['data'].get('reference'),
                    'metadata': result
                }
                
                if existing_verification:
                    # Update existing verification
                    for key, value in verification_data.items():
                        setattr(existing_verification, key, value)
                    existing_verification.save()
                    verification = existing_verification
                else:
                    # Create new verification
                    verification = BankAccountVerification.objects.create(
                        user=request.user,
                        account_number=account_number,
                        bank_code=bank_code,
                        **verification_data
                    )
                
                # Create or update bank account
                bank_account, created = BankAccount.objects.update_or_create(
                    user=request.user,
                    account_number=account_number,
                    bank_code=bank_code,
                    defaults={
                        'account_name': result['data']['account_name'],
                        'bank_name': bank_name,
                        'is_primary': not BankAccount.objects.filter(
                            user=request.user, 
                            is_primary=True
                        ).exists()
                    }
                )
            
            return Response({
                'status': True,
                'message': 'Account verified successfully',
                'data': BankAccountVerificationSerializer(verification).data
            })
            
        except requests.Timeout:
            error_message = 'Bank verification request timed out'
            status_code = status.HTTP_504_GATEWAY_TIMEOUT
        except requests.HTTPError as e:
            error_data = e.response.json() if e.response.content else {}
            error_message = error_data.get('message', 'Bank verification failed')
            status_code = e.response.status_code
        except requests.RequestException as e:
            error_message = f'Error connecting to Paystack: {str(e)}'
            status_code = status.HTTP_502_BAD_GATEWAY
        except Exception as e:
            error_message = f'Error verifying account: {str(e)}'
            status_code = status.HTTP_400_BAD_REQUEST
        
        # Log failed attempt - update existing or create new
        verification_data = {
            'status': 'failed',
            'metadata': {'error': error_message}
        }
        
        if existing_verification:
            # Update existing verification
            for key, value in verification_data.items():
                setattr(existing_verification, key, value)
            existing_verification.save()
        else:
            # Create new failed verification
            BankAccountVerification.objects.create(
                user=request.user,
                account_number=account_number,
                bank_code=bank_code,
                **verification_data
            )
        
        return Response(
            {'status': False, 'message': error_message},
            status=status_code
        )
        
    except Exception as e:
        return Response(
            {'status': False, 'message': f'An unexpected error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_virtual_account(request):
    serializer = CreateVirtualAccountSerializer(data=request.data)
    if serializer.is_valid():
        try:
            data = serializer.validated_data
            provider = VirtualAccountProvider.objects.get(id=data['provider_id'], is_active=True)
            
            # Check if user already has a virtual account
            existing_request = VirtualAccountRequest.objects.filter(
                user=request.user,
                status='created'
            ).first()
            
            if existing_request:
                return Response({
                    'message': 'Virtual account already exists',
                    'virtual_account': VirtualAccountRequestSerializer(existing_request).data
                })
            
            # Create virtual account request (placeholder - integrate with actual provider API)
            virtual_request = VirtualAccountRequest.objects.create(
                user=request.user,
                provider=provider,
                status='pending'
            )
            
            # TODO: Integrate with actual virtual account provider API
            # This is a placeholder implementation
            
            return Response({
                'message': 'Virtual account creation request submitted',
                'request_id': virtual_request.id
            })
            
        except VirtualAccountProvider.DoesNotExist:
            return Response({'error': 'Provider not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_virtual_account(request):
    try:
        virtual_account = VirtualAccountRequest.objects.filter(
            user=request.user,
            status='created'
        ).first()
        
        if virtual_account:
            return Response(VirtualAccountRequestSerializer(virtual_account).data)
        else:
            return Response({'message': 'No virtual account found'}, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BankAccountViewSet(mixins.CreateModelMixin,
                       mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.DestroyModelMixin,
                       GenericViewSet):
    """
    ViewSet for managing user bank accounts.
    """
    serializer_class = BankAccountSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return BankAccountVerification.objects.filter(user=self.request.user, status='verified')
    
    def perform_create(self, serializer):
        # The create method is handled by the serializer
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        """Set a bank account as primary."""
        account = self.get_object()
        
        # Set all accounts to not primary first
        BankAccountVerification.objects.filter(user=request.user).update(is_primary=False)
        
        # Set the selected account as primary
        account.is_primary = True
        account.save()
        
        return Response({
            'status': True,
            'message': 'Primary bank account updated successfully'
        })
    
    def destroy(self, request, *args, **kwargs):
        """Delete a bank account."""
        account = self.get_object()
        account.delete()
        
        return Response({
            'status': True,
            'message': 'Bank account deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


def get_bank_name(bank_code):
    """
    Get bank name from local database, cache, or Paystack API.
    
    Args:
        bank_code (str): The bank code to look up
        
    Returns:
        str: The bank name if found, 'Unknown Bank' otherwise
    """
    if not bank_code:
        return 'Unknown Bank'
    
    # Try to get from cache first
    cache_key = f'bank_name_{bank_code}'
    cached_name = cache.get(cache_key)
    if cached_name:
        return cached_name
    
    # Try to get from local database
    bank = Bank.objects.filter(code=bank_code, is_active=True).first()
    if bank:
        # Cache for 24 hours
        cache.set(cache_key, bank.name, 60 * 60 * 24)
        return bank.name
    
    # Fallback to hardcoded mapping
    bank_mapping = {
        '044': 'Access Bank',
        '023': 'Citibank',
        '063': 'Diamond Bank',
        '050': 'Ecobank',
        '070': 'Fidelity Bank',
        '011': 'First Bank',
        '214': 'First City Monument Bank',
        '058': 'Guaranty Trust Bank',
        '030': 'Heritage Bank',
        '301': 'Jaiz Bank',
        '082': 'Keystone Bank',
        '014': 'MainStreet Bank',
        '076': 'Polaris Bank',
        '101': 'Providus Bank',
        '221': 'Stanbic IBTC',
        '068': 'Standard Chartered',
        '232': 'Sterling Bank',
        '100': 'Suntrust Bank',
        '032': 'Union Bank',
        '033': 'United Bank for Africa',
        '215': 'Unity Bank',
        '035': 'Wema Bank',
        '057': 'Zenith Bank',
    }
    
    # If found in hardcoded mapping, cache it
    if bank_code in bank_mapping:
        cache.set(cache_key, bank_mapping[bank_code], 60 * 60 * 24)
        return bank_mapping[bank_code]
    
    # As a last resort, try to fetch from Paystack
    try:
        headers = {
            'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f"{PAYSTACK_BASE_URL}/bank",
            params={'country': 'Nigeria'},
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            banks = response.json().get('data', [])
            for bank_data in banks:
                if str(bank_data.get('code')) == str(bank_code):
                    bank_name = bank_data.get('name', 'Unknown Bank')
                    # Update local database for future use
                    Bank.objects.update_or_create(
                        code=bank_code,
                        defaults={
                            'name': bank_name,
                            'country': bank_data.get('country', 'Nigeria'),
                            'currency': bank_data.get('currency', 'NGN'),
                            'type': bank_data.get('type', 'nuban'),
                            'is_active': bank_data.get('active', True)
                        }
                    )
                    # Cache the result
                    cache.set(cache_key, bank_name, 60 * 60 * 24)
                    return bank_name
    except Exception as e:
        # Log the error but don't fail
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting bank name for code {bank_code}: {str(e)}")
    
    return 'Unknown Bank'
