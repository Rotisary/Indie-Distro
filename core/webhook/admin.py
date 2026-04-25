from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from unfold.admin import ModelAdmin

from .models import ProviderWebhookEvent


@admin.register(ProviderWebhookEvent)
class ProviderWebhookEventAdmin(ModelAdmin):
    fieldsets = (
        (
            _("Meta Information"),
            {
                "classes": ["tab"],
                "fields": (
                    "provider",
                    "event",
                    "processing_state",
                    "provider_status",
                    "tx_ref",
                    "provider_event_id",
                    "idempotency_key",
                ),
            },
        ),
        (
            _("Payload Data"),
            {
                "classes": ["tab"],
                "fields": ("payload", "handler_response"),
            },
        ),
        (
            _("Important dates"),
            {
                "classes": ["tab"],
                "fields": ("processed_at", "date_added", "date_last_modified"),
            },
        ),
    )

    list_display = [
        "provider",
        "event",
        "processing_state",
        "provider_status",
        "tx_ref",
        "processed_at",
    ]
    search_fields = ["provider", "event", "tx_ref", "provider_event_id"]
    readonly_fields = ["processed_at", "date_added", "date_last_modified"]
    ordering = ["-date_added"]
