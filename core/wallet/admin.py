from unfold.admin import ModelAdmin

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Wallet


@admin.register(Wallet)
class WalletAdmin(ModelAdmin):
    fieldsets = (
        (
            _("User"),
            {
                "classes": ["tab"],
                "fields": (
                    "owner",
                ),
            },
        ),
        (
            _("Meta Information"),
            {
                "classes": ["tab"],
                "fields": (
                    "account_reference",
                    "barter_id",
                    "virtual_account_number",
                    "virtual_bank_name",
                    "balance",
                    "wallet_pin",
                    "creation_status",
                ),
            },
        ),
        (
            _("Important dates"),
            {
                "classes": ["tab"],
                "fields": ("created_at", "date_added", "date_last_modified"),
            },
        ),
    )

    list_display = [
        "account_reference",
        "creation_status",
        "barter_id",
        "balance",
        "date_added",
    ]
    search_fields = ["account_reference", "barter_id"]
    readonly_fields = ["date_added", "date_last_modified"]
    ordering = ["-date_added"]