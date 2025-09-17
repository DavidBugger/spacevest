from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
import requests
from .models import CustomUser, BankAccount, VirtualAccount
from .serializers import CustomUserSerializer, BankAccountSerializer, VirtualAccountSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
import json

def home_view(request):
    """
    Home view for the application.
    """
    return render(request, 'users/landing.html', {})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_bank_account(request):
    """
    Verify a bank account using Paystack's resolve account number endpoint
    """
    try:
        data = json.loads(request.body)
        account_number = data.get('account_number')
        bank_code = data.get('bank_code')
        
        if not account_number or not bank_code:
            return Response(
                {'error': 'Account number and bank code are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Call Paystack API to resolve account number
        headers = {
            'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
            'Content-Type': 'application/json',
        }
        
        response = requests.get(
            f'https://api.paystack.co/bank/resolve?account_number={account_number}&bank_code={bank_code}',
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            return Response({
                'account_name': data['data']['account_name'],
                'account_number': account_number,
                'bank_code': bank_code,
                'bank_name': data['data'].get('bank_name', '')
            })
            
        return Response(
            {'error': 'Could not verify account details'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
        
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def dashboard_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    context = {
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY
    }
    return render(request, 'users/dashboard.html', context)

def login_view(request):
    """
    Login page view.
    """
    return render(request, 'users/login.html', {})


def register_view(request):
    """
    Register page view.
    """
    return render(request, 'users/register.html', {})

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

class BankAccountListView(generics.ListCreateAPIView):
    serializer_class = BankAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class BankAccountDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BankAccountSerializer

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user)

class VirtualAccountView(generics.RetrieveAPIView):
    serializer_class = VirtualAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        try:
            return VirtualAccount.objects.get(user=self.request.user)
        except VirtualAccount.DoesNotExist:
            return None

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_virtual_account(request):
    """
    Generate a dedicated virtual account for the user using Paystack API
    """
    user = request.user

    # Check if user already has a virtual account
    existing_account = VirtualAccount.objects.filter(user=user).first()
    if existing_account:
        serializer = VirtualAccountSerializer(existing_account)
        return Response({
            'message': 'Virtual account already exists',
            'virtual_account': serializer.data
        }, status=status.HTTP_200_OK)

    # Paystack API endpoint and headers
    url = "https://api.paystack.co/dedicated_account"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    # Request payload
    data = {
        "customer": user.id,  # Using user ID as customer identifier
        "preferred_bank": "wema-bank"  # You can make this configurable
    }

    try:
        # Make API call to Paystack
        response = requests.post(url, json=data, headers=headers)
        response_data = response.json()

        if response.status_code == 200 and response_data.get('status'):
            account_data = response_data.get('data', {})

            # Create virtual account record
            virtual_account = VirtualAccount.objects.create(
                user=user,
                bank_name=account_data.get('bank', {}).get('name', 'Wema Bank'),
                account_number=account_data.get('account_number'),
                account_name=account_data.get('account_name'),
                provider_reference=account_data.get('account_number'),  # Using account number as reference
                is_active=True
            )

            serializer = VirtualAccountSerializer(virtual_account)
            return Response({
                'message': 'Virtual account generated successfully',
                'virtual_account': serializer.data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'error': response_data.get('message', 'Failed to generate virtual account')
            }, status=status.HTTP_400_BAD_REQUEST)

    except requests.RequestException as e:
        return Response({
            'error': f'Network error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return Response({
            'error': f'Server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_payment_sent(request):
    """
    Handle user confirmation that they have sent money to virtual account
    This would typically trigger a webhook check or manual verification
    """
    user = request.user

    try:
        virtual_account = VirtualAccount.objects.get(user=user, is_active=True)
    except VirtualAccount.DoesNotExist:
        return Response({
            'error': 'No active virtual account found'
        }, status=status.HTTP_404_NOT_FOUND)

    # For now, we'll simulate a payment confirmation
    # In production, this should check Paystack webhooks or API for actual payments
    amount = request.data.get('amount')
    if not amount:
        return Response({
            'error': 'Amount is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Invalid amount")

        # Credit the user's wallet
        user.wallet_balance += amount
        user.save()

        # Create a transaction record
        from transactions.models import Transaction
        Transaction.objects.create(
            user=user,
            transaction_type='credit',
            category='deposit',
            amount=amount,
            description=f'Wallet top-up via virtual account {virtual_account.account_number}',
            status='completed',
            metadata={
                'payment_method': 'virtual_account',
                'account_number': virtual_account.account_number,
                'bank_name': virtual_account.bank_name
            }
        )

        return Response({
            'message': f'Wallet credited with ₦{amount}',
            'new_balance': user.wallet_balance
        }, status=status.HTTP_200_OK)

    except ValueError:
        return Response({
            'error': 'Invalid amount format'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': f'Error processing payment: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_user(request):
    serializer = CustomUserSerializer(data=request.data)
    if serializer.is_valid():
        user = CustomUser.objects.create_user(
            email=serializer.validated_data['email'],
            username=serializer.validated_data['username'],
            password=request.data.get('password'),
            first_name=serializer.validated_data.get('first_name', ''),
            last_name=serializer.validated_data.get('last_name', ''),
            phone=serializer.validated_data.get('phone', ''),
            country=serializer.validated_data.get('country', 'Nigeria')
        )
        return Response(CustomUserSerializer(user).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@csrf_protect
def login_user(request):
    from django.contrib.auth import authenticate
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return Response({'message': 'Login successful'}, status=status.HTTP_200_OK)
    return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_user(request):
    logout(request)
    return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_dashboard(request):
    user = request.user
    data = {
        'user': CustomUserSerializer(user).data,
        'wallet_balance': user.wallet_balance,
        'kyc_verified': user.kyc_verified,
        'points': user.points
    }
    return Response(data, status=status.HTTP_200_OK)

from django.conf import settings

@login_required
def dashboard_view(request):
    context = {
        'user': request.user,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY
    }
    return render(request, 'users/dashboard.html', context)
