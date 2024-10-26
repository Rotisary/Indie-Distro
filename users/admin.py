from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Wallet, SubAccount, Bank

class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'username', 'date_joined']
    search_fields = ['email', 'username']
    readonly_fields = ['date_joined', 'last_login']

    filter_horizontal = ()
    list_filter = ()
    fieldsets = ()


class WalletAdmin(admin.ModelAdmin):
    list_display = ['get_name', 'wallet_id', 'wallet_number', 'balance']
    search_fields = ['wallet_id',  'user__username', 'user__name', 'wallet_number']
    list_select_related = ['user']


    @admin.display(description="wallet user's name")
    def get_name(self, obj):
        return obj.user.name
    

class SubAccountAdmin(admin.ModelAdmin):
    list_display = ['account_reference', 'barter_id', 'virtual_account_number', 'virtual_bank_name']
    search_fields = ['account_reference', 'barter_id', 'virtual_account_number', 'virtual_bank_name']
    list_select_related = ['wallet']


    @admin.display(description='wallet id')
    def get_wallet(self, obj):
        return obj.wallet.wallet_id


class BankAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']
    search_fields = ['name', 'code']

admin.site.register(User, CustomUserAdmin)
admin.site.register(Wallet, WalletAdmin)
admin.site.register(SubAccount, SubAccountAdmin)
admin.site.register(Bank, BankAdmin)
