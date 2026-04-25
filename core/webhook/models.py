from django.db import models
from django.db.models import JSONField

from core.utils import enums
from core.utils.mixins.base import BaseModelMixin


class ProviderWebhookEvent(BaseModelMixin):
    provider = models.CharField(
        max_length=30,
        choices=enums.WebhookProvider.choices(),
    )
    event = models.CharField(max_length=60)
    idempotency_key = models.CharField(max_length=255, unique=True)
    tx_ref = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    provider_event_id = models.CharField(
        max_length=100, null=True, blank=True, db_index=True
    )
    provider_status = models.CharField(max_length=50, null=True, blank=True)
    payload = JSONField(default=dict, blank=True)
    handler_response = JSONField(default=dict, blank=True)
    processing_state = models.CharField(
        max_length=20,
        choices=enums.WebhookProcessingState.choices(),
        default=enums.WebhookProcessingState.RECEIVED.value,
    )
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-date_added"]

    def __str__(self):
        return f"{self.provider}:{self.event}:{self.tx_ref or self.provider_event_id or self.id}"
