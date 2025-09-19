from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import render, redirect, reverse
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.contrib import messages
from django.contrib.messages import get_messages
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
import requests
from django.conf import settings
import logging
import string
from .models import CustomUser, BankAccount, VirtualAccount, PasswordResetToken
from .serializers import CustomUserSerializer, BankAccountSerializer, VirtualAccountSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from datetime import timedelta
import secrets
import string
import json
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.hashers import make_password

import logging

logger = logging.getLogger(__name__)

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

@login_required
def bank_verification_view(request):
    """
    Bank account verification page view.
    """
    context = {
        'user': request.user,
        'bank_accounts': request.user.bankaccount_set.all(),
        'verifications': BankAccountVerification.objects.filter(user=request.user)
    }
    return render(request, 'users/bank_verification.html', context)

def dashboard_view(request):
    """
    Dashboard view for authenticated users.
    """
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Get user's verified bank account
    bank_account = None
    if hasattr(request.user, 'bank_verifications'):
        # First try to get the primary verified account
        bank_account = request.user.bank_verifications.filter(
            status='verified',
            is_primary=True
        ).first()
        
        # If no primary, get any verified account
        if not bank_account:
            bank_account = request.user.bank_verifications.filter(
                status='verified'
            ).first()
    
    context = {
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
        'bank_account': bank_account,
        'virtual_account': getattr(request.user, 'virtual_account', None)
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

# Set up logging
logger = logging.getLogger(__name__)

def password_reset_request(request):
    """
    Handle password reset request. Shows a form for email input and processes the form submission.
    Handles both form submissions and JSON API requests.
    """
    logger.info(f"Password reset request received. Method: {request.method}, Content-Type: {request.content_type}")
    
    if request.method == 'GET':
        logger.debug("Serving password reset form")
        return render(request, 'users/forgot_password.html')
    
    # Handle POST request
    try:
        # Check if the request is JSON
        if request.content_type == 'application/json':
            logger.debug("Processing JSON request")
            try:
                data = json.loads(request.body)
                email = data.get('email')
                logger.debug(f"Received email from JSON: {email}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
        else:
            # Regular form submission
            email = request.POST.get('email')
            logger.debug(f"Received email from form: {email}")
        
        if not email:
            logger.warning("No email provided in the request")
            if request.content_type == 'application/json':
                return JsonResponse({'error': 'Email is required'}, status=400)
            messages.error(request, 'Email is required')
            return render(request, 'users/forgot_password.html')
        
        try:
            logger.debug(f"Looking up user with email: {email}")
            user = CustomUser.objects.get(email=email)
            logger.debug(f"Found user: {user.username} (ID: {user.id})")
            
            # Generate a token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            logger.debug(f"Generated token for user {user.id}")
            
            # Create reset URL - using the backend URL since we're handling the reset form in Django
            reset_url = request.build_absolute_uri(
                reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            )
            logger.debug(f"Reset URL: {reset_url}")
            
            # Prepare email content
            subject = 'Password Reset Request'
            email_context = {
                'user': user,
                'reset_url': reset_url,
                'expiry_hours': 24
            }
            
            logger.debug("Rendering email template")
            html_message = render_to_string('users/emails/password_reset_email.html', email_context)
            plain_message = strip_tags(html_message)
            
            logger.info(f"Sending password reset email to {user.email}")
            try:
                send_mail(
                    subject=subject,
                    message=plain_message,
                    html_message=html_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception as e:
                logger.error(f"Failed to send password reset email: {str(e)}", exc_info=True)
                if request.content_type == 'application/json':
                    return JsonResponse(
                        {'error': 'Failed to send password reset email. Please try again later.'},
                        status=500
                    )
                messages.error(request, 'Failed to send password reset email. Please try again.')
                return render(request, 'users/forgot_password.html')
            logger.info("Password reset email sent successfully")
            
            # Return appropriate response based on request type
            success_message = 'If an account exists with this email, a password reset link has been sent.'
            logger.info(success_message)
            
            if request.content_type == 'application/json':
                return JsonResponse(
                    {'message': success_message},
                    status=200
                )
            messages.success(request, success_message)
            return render(request, 'users/forgot_password.html')
            
        except CustomUser.DoesNotExist:
            # Don't reveal that the user doesn't exist for security reasons
            logger.warning(f"Password reset requested for non-existent email: {email}")
            security_message = 'If an account exists with this email, a password reset link has been sent.'
            
            if request.content_type == 'application/json':
                return JsonResponse(
                    {'message': security_message},
                    status=200
                )
            messages.success(request, security_message)
            return render(request, 'users/forgot_password.html')
        
        except Exception as e:
            error_msg = f"Error in password reset process: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            if request.content_type == 'application/json':
                return JsonResponse(
                    {'error': 'An error occurred while processing your request. Please try again later.'},
                    status=500
                )
            messages.error(request, 'An error occurred while processing your request. Please try again later.')
            return render(request, 'users/forgot_password.html')

    except Exception as e:
        if request.content_type == 'application/json':
            return JsonResponse(
                {'error': 'An error occurred while processing your request. Please try again later.'},
                status=500
            )
        messages.error(request, 'An error occurred while processing your request. Please try again later.')
        return render(request, 'users/forgot_password.html')

def password_reset_confirm(request, uidb64=None, token=None):
    """
    Handle password reset confirmation with the new password.
    """
    # Handle GET request - show the password reset form
    if request.method == 'GET':
        if not uidb64 or not token:
            messages.error(request, 'Invalid password reset link.')
            return redirect('login')
            
        try:
            # Verify the token and uidb64
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)
            
            if not default_token_generator.check_token(user, token):
                messages.error(request, 'The password reset link is invalid or has expired.')
                return redirect('login')
                
            return render(request, 'users/password_reset_confirm.html', {
                'uidb64': uidb64,
                'token': token,
                'validlink': True
            })
            
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist) as e:
            logger.error(f'Error in password reset confirmation: {str(e)}')
            messages.error(request, 'The password reset link is invalid or has expired.')
            return redirect('login')
    
    # Handle POST request - process the form submission
    elif request.method == 'POST':
        try:
            # Check if it's a JSON request
            if request.headers.get('Content-Type') == 'application/json':
                data = json.loads(request.body)
                uidb64 = data.get('uidb64')
                token = data.get('token')
                new_password1 = data.get('new_password1')
                new_password2 = data.get('new_password2')
                is_json = True
            else:
                uidb64 = request.POST.get('uidb64')
                token = request.POST.get('token')
                new_password1 = request.POST.get('new_password1')
                new_password2 = request.POST.get('new_password2')
                is_json = False
            
            # Validate required fields
            if not all([uidb64, token, new_password1, new_password2]):
                error_msg = 'All fields are required.'
                if is_json:
                    return JsonResponse({'error': error_msg}, status=400)
                messages.error(request, error_msg)
                return render(request, 'users/password_reset_confirm.html', {
                    'uidb64': uidb64,
                    'token': token,
                    'validlink': True
                })
            
            # Validate password match
            if new_password1 != new_password2:
                error_msg = 'Passwords do not match.'
                if is_json:
                    return JsonResponse({'error': error_msg}, status=400)
                messages.error(request, error_msg)
                return render(request, 'users/password_reset_confirm.html', {
                    'uidb64': uidb64,
                    'token': token,
                    'validlink': True
                })
            
            # Validate password strength
            if len(new_password1) < 8 or not any(char.isdigit() for char in new_password1) or not any(char in string.punctuation for char in new_password1):
                error_msg = 'Password must be at least 8 characters long and include numbers and special characters.'
                if is_json:
                    return JsonResponse({'error': error_msg}, status=400)
                messages.error(request, error_msg)
                return render(request, 'users/password_reset_confirm.html', {
                    'uidb64': uidb64,
                    'token': token,
                    'validlink': True
                })
            
            try:
                # Decode user ID
                uid = force_str(urlsafe_base64_decode(uidb64))
                user = CustomUser.objects.get(pk=uid)
                
                # Verify token
                if not default_token_generator.check_token(user, token):
                    error_msg = 'The password reset link is invalid or has expired.'
                    if is_json:
                        return JsonResponse({'error': error_msg}, status=400)
                    messages.error(request, error_msg)
                    return redirect('login')
                
                # Update password
                user.set_password(new_password1)
                user.save()
                
                success_msg = 'Your password has been reset successfully. You can now log in with your new password.'
                if is_json:
                    return JsonResponse({'success': success_msg}, status=200)
                    
                messages.success(request, success_msg)
                return redirect('login')
                
            except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist) as e:
                logger.error(f'Error in password reset: {str(e)}')
                error_msg = 'The password reset link is invalid or has expired.'
                if is_json:
                    return JsonResponse({'error': error_msg}, status=400)
                messages.error(request, error_msg)
                return redirect('login')
                
        except json.JSONDecodeError:
            error_msg = 'Invalid JSON data'
            if is_json:
                return JsonResponse({'error': error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect('login')
            
        except Exception as e:
            logger.error(f'Unexpected error in password reset: {str(e)}')
            error_msg = 'An error occurred while processing your request. Please try again.'
            if is_json:
                return JsonResponse({'error': error_msg}, status=500)
            messages.error(request, error_msg)
            return redirect('login')
    
    # If not GET or POST, redirect to login
    return redirect('login')
    
    # If not GET or POST, redirect to login
    return redirect('login')

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
    return Response({
        'user': CustomUserSerializer(user).data,
        'wallet_balance': user.wallet_balance,
    })

