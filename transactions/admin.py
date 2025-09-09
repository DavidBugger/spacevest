from django.contrib import admin
from .models import Transaction, TransactionFee, CryptoTransaction, AirtimeTransaction, DataTransaction

class TransactionFeeInline(admin.TabularInline):
    model = TransactionFee
    extra = 0

class CryptoTransactionInline(admin.TabularInline):
    model = CryptoTransaction
    extra = 0

class AirtimeTransactionInline(admin.TabularInline):
    model = AirtimeTransaction
    extra = 0

class DataTransactionInline(admin.TabularInline):
    model = DataTransaction
    extra = 0

class TransactionAdmin(admin.ModelAdmin):
    list_display = ('reference', 'user', 'transaction_type', 'category', 'amount', 'status', 'created_at')
    list_filter = ('transaction_type', 'category', 'status', 'created_at')
    search_fields = ('reference', 'user__email', 'user__username', 'description')
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
    inlines = [TransactionFeeInline, CryptoTransactionInline, AirtimeTransactionInline, DataTransactionInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'transaction_type', 'category', 'amount', 'status', 'description', 'reference')
        }),
        ('Transfer Details', {
            'fields': ('recipient', 'recipient_email', 'bank_account'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )

class TransactionFeeAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'amount', 'description', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('transaction__reference', 'description')

class CryptoTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'cryptocurrency', 'amount_crypto', 'exchange_rate', 'network')
    list_filter = ('cryptocurrency', 'network')
    search_fields = ('transaction__reference', 'wallet_address')

class AirtimeTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'phone_number', 'network', 'plan_name')
    list_filter = ('network',)
    search_fields = ('transaction__reference', 'phone_number')

class DataTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'phone_number', 'network', 'data_plan', 'validity')
    list_filter = ('network',)
    search_fields = ('transaction__reference', 'phone_number', 'data_plan')

admin.site.register(Transaction, TransactionAdmin)
admin.site.register(TransactionFee, TransactionFeeAdmin)
admin.site.register(CryptoTransaction, CryptoTransactionAdmin)
admin.site.register(AirtimeTransaction, AirtimeTransactionAdmin)
admin.site.register(DataTransaction, DataTransactionAdmin)
