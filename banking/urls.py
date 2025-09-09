from django.urls import path
from . import views

urlpatterns = [
    path('banks/', views.BankListView.as_view(), name='bank-list'),
    path('verifications/', views.BankAccountVerificationListView.as_view(), name='verification-list'),
    path('verify-account/', views.verify_bank_account, name='verify-account'),
    path('virtual-account/create/', views.create_virtual_account, name='create-virtual-account'),
    path('virtual-account/', views.get_virtual_account, name='get-virtual-account'),
]
