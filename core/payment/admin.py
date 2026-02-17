from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from .models import LedgerAccount, Transaction, LedgerJournal, JournalEntry


@admin.register(LedgerAccount)
class LedgerAccountAdmin(ModelAdmin):
    fieldsets = (
        (
            _("Owner"),
            {
                "classes": ["tab"],
                "fields": ("owner",),
            },
        ),
        (
            _("Personal Info"),
            {
                "classes": ["tab"],
                "fields": (
                    "type",
                    "currency",
                ),
            },
        ),
        (
            _("Important dates"),
            {
                "classes": ["tab"],
                "fields": ("date_added", "date_last_modified"),
            },
        ),
    )

    list_display = ["owner__first_name", "owner__last_name", "type", "currency"]
    search_fields = ["owner__first_name", "owner__last_name", "type"]
    readonly_fields = ["date_added", "date_last_modified"]
    ordering = ["-date_added"]


@admin.register(Transaction)
class TransactionAdmin(ModelAdmin):
    fieldsets = (
        (
            _("Personal Info"),
            {
                "classes": ["tab"],
                "fields": (
                    "reference",
                    "status",
                    "description",
                    "currency",
                    "metadata"
                ),
            },
        ),
        (
            _("Important dates"),
            {
                "classes": ["tab"],
                "fields": ("successful_at", "date_added", "date_last_modified"),
            },
        ),
    )

    list_display = ["reference", "status", "currency", "successful_at"]
    search_fields = ["reference"]
    readonly_fields = ["date_added", "date_last_modified", "successful_at"]
    ordering = ["-date_added"]


@admin.register(LedgerJournal)
class LedgerJournalAdmin(ModelAdmin):
    fieldsets = (
        (
            _("Personal Info"),
            {
                "classes": ["tab"],
                "fields": (
                    "transaction",
                ),
            },
        ),
        (
            _("Important dates"),
            {
                "classes": ["tab"],
                "fields": ("date_added", "date_last_modified"),
            },
        ),
    )

    list_display = ["id", "transaction__reference"]
    search_fields = ["transaction__reference"]
    readonly_fields = ["date_added", "date_last_modified"]
    ordering = ["-date_added"]


@admin.register(JournalEntry)
class JournalEntryAdmin(ModelAdmin):
    fieldsets = (
        (
            _("Personal Info"),
            {
                "classes": ["tab"],
                "fields": (
                    "account",
                    "journal",
                    "line_no",
                    "type",
                    "status",
                    "amount"
                ),
            },
        ),
        (
            _("Important dates"),
            {
                "classes": ["tab"],
                "fields": ("completed_at", "date_added", "date_last_modified"),
            },
        ),
    )

    list_display = [
        "id", 
        "journal__transaction__reference", 
        "account__type", 
        "line_no", 
        "type", 
        "status", 
        "completed_at"
    ]
    search_fields = ["journal__transaction__reference"]
    readonly_fields = ["date_added", "date_last_modified", "completed_at"]
    ordering = ["-date_added"]