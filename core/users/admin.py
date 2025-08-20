from django.contrib import admin
from unfold.admin import ModelAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import Group
from .models import User, UserSession

admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "first_name", "last_name", "password1", "password2"),
            },
        ),
    )

    fieldsets = (
        (
            _("User"),
            {
                "classes": ["tab"],
                "fields": (
                    "email",
                    "username",
                    "password",
                ),
            },
        ),
        (
            _("Personal info"),
            {
                "classes": ["tab"],
                "fields": (
                    "first_name",
                    "last_name",
                    "bio",
                    "gender",
                    "dob",
                    "location",
                ),
            },
        ),
        (
            _("Meta Information"),
            {
                "classes": ["tab"],
                "fields": (
                    "phone_number",
                    "is_phone_number_verified",
                    "is_email_verified",
                    "is_creator",
                    "account_type",
                    "total_earned",
                ),
            },
        ),
        (
            _("Permissions"),
            {
                "classes": ["tab"],
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_banned",
                    "user_permissions",
                ),
            },
        ),
        (
            _("Important dates"),
            {
                "classes": ["tab"],
                "fields": ("last_login", "date_added", "date_last_modified"),
            },
        ),
    )

    list_display = [
        "email",
        "username",
        "id",
        "account_type",
    ]
    search_fields = ["email", "username", "first_name", "last_name"]
    readonly_fields = ["date_added", "date_last_modified"]
    ordering = ["email"]


@admin.register(UserSession)
class AccountSessionAdmin(ModelAdmin):
    list_display = ["user", "ip_address", "user_agent"]


# class WalletAdmin(admin.ModelAdmin):
#     list_display = ['get_name', 'wallet_id', 'wallet_number', 'balance']
#     search_fields = ['wallet_id',  'user__username', 'user__name', 'wallet_number']
#     list_select_related = ['user']


#     @admin.display(description="wallet user's name")
#     def get_name(self, obj):
#         return obj.user.name
    

# class SubAccountAdmin(admin.ModelAdmin):
#     list_display = ['account_reference', 'barter_id', 'virtual_account_number', 'virtual_bank_name']
#     search_fields = ['account_reference', 'barter_id', 'virtual_account_number', 'virtual_bank_name']
#     list_select_related = ['wallet']


#     @admin.display(description='wallet id')
#     def get_wallet(self, obj):
#         return obj.wallet.wallet_id


# class BankAdmin(admin.ModelAdmin):
#     list_display = ['name', 'code']
#     search_fields = ['name', 'code']
