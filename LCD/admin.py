from django.contrib import admin
from .models import LCD, Brand, Wallet

@admin.register(LCD)
class LCDAdmin(admin.ModelAdmin):
    list_display = ['id','title', 'buy_price', 'sell_price', 'updated_at']
    list_filter = ['brand','buy_price', 'sell_price','buy_price', 'updated_at']
    readonly_fields = ('created_at','updated_at')
    search_fields = ['title', 'brand__title']

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    pass


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    pass