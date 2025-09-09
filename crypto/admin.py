from django.contrib import admin
from .models import CryptoRate, CryptoPriceHistory, SupportedCrypto

class CryptoPriceHistoryInline(admin.TabularInline):
    model = CryptoPriceHistory
    extra = 0
    readonly_fields = ('timestamp',)

class CryptoRateAdmin(admin.ModelAdmin):
    list_display = ('cryptocurrency', 'symbol', 'current_price_ngn', 'current_price_usd', 'last_updated')
    list_filter = ('last_updated',)
    search_fields = ('cryptocurrency', 'symbol')
    readonly_fields = ('last_updated',)
    inlines = [CryptoPriceHistoryInline]

class CryptoPriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('crypto_rate', 'price_ngn', 'price_usd', 'timestamp')
    list_filter = ('timestamp', 'crypto_rate')
    search_fields = ('crypto_rate__cryptocurrency', 'crypto_rate__symbol')
    readonly_fields = ('timestamp',)

class SupportedCryptoAdmin(admin.ModelAdmin):
    list_display = ('name', 'symbol', 'is_active', 'min_purchase_amount', 'max_purchase_amount', 'network_fee')
    list_filter = ('is_active',)
    search_fields = ('name', 'symbol')
    list_editable = ('is_active', 'min_purchase_amount', 'max_purchase_amount', 'network_fee')

admin.site.register(CryptoRate, CryptoRateAdmin)
admin.site.register(CryptoPriceHistory, CryptoPriceHistoryAdmin)
admin.site.register(SupportedCrypto, SupportedCryptoAdmin)
