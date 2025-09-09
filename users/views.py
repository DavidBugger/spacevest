from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import render
from django.http import JsonResponse
from .models import CustomUser, BankAccount, VirtualAccount
from .serializers import CustomUserSerializer, BankAccountSerializer, VirtualAccountSerializer

def home_view(request):
    """
    Home view for the application.
    """
    return render(request, 'users/landing.html', {})




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
