from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
import requests
from decouple import config
from django.db import transaction as db_transaction
from .models import Bank, BankAccountVerification, VirtualAccountProvider, VirtualAccountRequest
from .serializers import (
    BankSerializer, BankAccountVerificationSerializer, VirtualAccountRequestSerializer,
    VerifyAccountSerializer, CreateVirtualAccountSerializer
)
from users.models import BankAccount

PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY')
PAYSTACK_BASE_URL = 'https://api.paystack.co'

class BankListView(generics.ListAPIView):
    queryset = Bank.objects.filter(is_active=True).order_by('name')
    serializer_class = BankSerializer
    permission_classes = [AllowAny]

class BankAccountVerificationListView(generics.ListAPIView):
    serializer_class = BankAccountVerificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BankAccountVerification.objects.filter(user=self.request.user)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_bank_account(request):
    serializer = VerifyAccountSerializer(data=request.data)
    if serializer.is_valid():
        try:
            data = serializer.validated_data
            
            # Check if already verified
            existing_verification = BankAccountVerification.objects.filter(
                user=request.user,
                account_number=data['account_number'],
                bank_code=data['bank_code'],
                status='verified'
            ).first()
            
            if existing_verification:
                return Response({
                    'message': 'Account already verified',
                    'verification': BankAccountVerificationSerializer(existing_verification).data
                })
            
            # Call Paystack API for verification
            headers = {
                'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{PAYSTACK_BASE_URL}/bank/resolve",
                params={
                    'account_number': data['account_number'],
                    'bank_code': data['bank_code']
                },
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Create verification record
                verification = BankAccountVerification.objects.create(
                    user=request.user,
                    account_number=data['account_number'],
                    bank_code=data['bank_code'],
                    account_name=result['data']['account_name'],
                    status='verified',
                    verification_reference=result['data'].get('reference'),
                    metadata=result
                )
                
                # Create or update bank account
                bank_account, created = BankAccount.objects.update_or_create(
                    user=request.user,
                    account_number=data['account_number'],
                    bank_code=data['bank_code'],
                    defaults={
                        'account_name': result['data']['account_name'],
                        'bank_name': get_bank_name(data['bank_code']),
                        'is_primary': not BankAccount.objects.filter(user=request.user, is_primary=True).exists()
                    }
                )
                
                return Response(BankAccountVerificationSerializer(verification).data)
            
            else:
                # Create failed verification record
                verification = BankAccountVerification.objects.create(
                    user=request.user,
                    account_number=data['account_number'],
                    bank_code=data['bank_code'],
                    status='failed',
                    metadata=response.json() if response.content else {}
                )
                
                return Response({
                    'error': 'Account verification failed',
                    'details': response.json() if response.content else 'Unknown error'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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

def get_bank_name(bank_code):
    # Simple mapping of common Nigerian bank codes to names
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
    return bank_mapping.get(bank_code, 'Unknown Bank')
