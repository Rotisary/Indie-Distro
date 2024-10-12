from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Wallet

class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'username', 'date_joined']
    search_fields = ['email', 'username']
    readonly_fields = ['date_joined', 'last_login']

    filter_horizontal = ()
    list_filter = ()
    fieldsets = ()


class WalletAdmin(admin.ModelAdmin):
    list_display = ['wallet_id', 'user__name', 'wallet_number', 'balance']
    search_fields = ['wallet_id',  'user__username', 'user__name', 'wallet_number']


admin.site.register(User, CustomUserAdmin)
admin.site.register(Wallet, WalletAdmin)
