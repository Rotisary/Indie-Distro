from typing import Optional

from django.db.models import Q

from core.webhook.models import WebhookEndpoint
from core.webhook.tasks import deliver_webhook

from .payload import *


def trigger_webhooks(
    event: str, 
    payload: dict,
        *, 
    owner_id: Optional[int] = None
) -> int:
    """
    Enqueue deliveries to all active endpoints subscribed to 'event'.
    If owner_id is provided, sends to that user's endpoints and global (owner=None).
    Returns count of enqueued deliveries.
    """
    q = Q(is_active=True, event=event)
    if owner_id is not None:
        q &= (Q(owner__id=owner_id) | Q(owner__isnull=True))
    endpoints = WebhookEndpoint.objects.filter(q).only("id", "target_url", "secret", "headers")
    count = 0
    for ep in endpoints:
        deliver_webhook.delay(ep.id, event, payload, attempt=1)
        count += 1
    return count