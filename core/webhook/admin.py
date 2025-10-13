from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from .models import WebhookEndpoint


@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(ModelAdmin):
    list_display = ["event", "is_active", "last_sent_at"]
    search_fields = ["event"]
    readonly_fields = ["date_added", "date_last_modified"]
    ordering = ["last_sent_at"]
