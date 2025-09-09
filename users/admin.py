from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, BankAccount, VirtualAccount

class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'phone', 'wallet_balance', 'kyc_verified', 'role', 'is_staff', 'is_active')
    list_filter = ('kyc_verified', 'role', 'is_staff', 'is_active', 'created_at')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'phone')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone', 'country')}),
        ('Financial Info', {'fields': ('wallet_balance',)}),
        ('KYC & Verification', {'fields': ('kyc_verified', 'kyc_details')}),
        ('Security & Preferences', {'fields': ('security_settings', 'preferences')}),
        ('Points & Rewards', {'fields': ('points',)}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'date_joined', 'last_login')
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'first_name', 'last_name', 'phone', 'country'),
        }),
    )

class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('account_name', 'bank_name', 'account_number', 'user', 'is_primary', 'created_at')
    list_filter = ('bank_name', 'is_primary', 'created_at')
    search_fields = ('account_name', 'account_number', 'user__email', 'user__username')
    readonly_fields = ('created_at', 'updated_at')

class VirtualAccountAdmin(admin.ModelAdmin):
    list_display = ('account_name', 'bank_name', 'account_number', 'user', 'is_active', 'created_at')
    list_filter = ('bank_name', 'is_active', 'created_at')
    search_fields = ('account_name', 'account_number', 'user__email', 'user__username')
    readonly_fields = ('created_at', 'updated_at')

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(BankAccount, BankAccountAdmin)
admin.site.register(VirtualAccount, VirtualAccountAdmin)
