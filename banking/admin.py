from django.contrib import admin
from .models import Bank, BankAccountVerification, VirtualAccountProvider, VirtualAccountRequest, WebhookEvent

class BankAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'country', 'is_active', 'created_at')
    list_filter = ('is_active', 'country', 'created_at')
    search_fields = ('name', 'code')
    list_editable = ('is_active',)

class BankAccountVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'account_number', 'bank_code', 'account_name', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'user__username', 'account_number', 'bank_code')
    readonly_fields = ('created_at', 'updated_at')

class VirtualAccountProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at',)

class VirtualAccountRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'account_number', 'account_name', 'status', 'created_at')
    list_filter = ('status', 'provider', 'created_at')
    search_fields = ('user__email', 'user__username', 'account_number', 'provider_reference')
    readonly_fields = ('created_at', 'updated_at')

class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'provider', 'processed', 'created_at')
    list_filter = ('event_type', 'provider', 'processed', 'created_at')
    search_fields = ('provider', 'event_type')
    readonly_fields = ('created_at', 'processed_at')

admin.site.register(Bank, BankAdmin)
admin.site.register(BankAccountVerification, BankAccountVerificationAdmin)
admin.site.register(VirtualAccountProvider, VirtualAccountProviderAdmin)
admin.site.register(VirtualAccountRequest, VirtualAccountRequestAdmin)
admin.site.register(WebhookEvent, WebhookEventAdmin)
