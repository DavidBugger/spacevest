from django.urls import path, re_path
from . import views
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

urlpatterns = [
    # Authentication endpoints
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    
    # User profile endpoints
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('dashboard/', views.user_dashboard, name='user-dashboard'),
    
    # Bank account endpoints
    path('bank-accounts/verify/', login_required(views.bank_verification_view), name='bank-verification'),
    path('bank-accounts/', views.BankAccountListView.as_view(), name='bank-account-list'),
    path('bank-accounts/<int:pk>/', views.BankAccountDetailView.as_view(), name='bank-account-detail'),
    path('bank-accounts/verify/', views.verify_bank_account, name='verify-bank-account'),
    
    # Virtual account endpoints
    path('virtual-account/', views.VirtualAccountView.as_view(), name='virtual-account'),
    path('virtual-account/generate/', views.generate_virtual_account, name='generate-virtual-account'),
    path('virtual-account/confirm-payment/', views.confirm_payment_sent, name='confirm-payment-sent'),
    
    # Password reset endpoint
    path('forgot-password/', views.password_reset_request, name='password_reset'),
]

# Add this to the main urls.py file for the dashboard view
# path('dashboard/', views.dashboard_view, name='dashboard'),
