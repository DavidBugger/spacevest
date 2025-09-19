from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router for the BankAccountViewSet
router = DefaultRouter()
router.register(r'accounts', views.BankAccountViewSet, basename='bankaccount')

urlpatterns = [
    # Include the router URLs
    path('', include(router.urls)),
    
    # Existing URLs
    path('banks/', views.BankListView.as_view(), name='bank-list'),
    path('verifications/', views.BankAccountVerificationListView.as_view(), name='verification-list'),
    path('verify-account/', views.verify_bank_account, name='verify-account'),
    path('virtual-account/create/', views.create_virtual_account, name='create-virtual-account'),
    path('virtual-account/', views.get_virtual_account, name='get-virtual-account'),
]
