from celery import shared_task
from loguru import logger

from django.utils import timezone

from .models import WebhookEndpoint
from core.utils.helpers.webhook import WebhookUtils


BACKOFF = [60, 300, 900, 3600] 


@shared_task(bind=True, max_retries=len(BACKOFF), retry_backoff=False)
def deliver_webhook(
    self, 
    endpoint_id: int, 
    event: str, 
    payload: dict, 
    attempt: int = 1
):
    endpoint = WebhookEndpoint.objects.get(pk=endpoint_id, is_active=True)
    if not endpoint:
        logger.warning(
            f"Webhook endpoint {endpoint_id} not found or inactive; skip.")
        return

    res = WebhookUtils._send(endpoint, event, payload, attempt)

    endpoint.last_sent_at = timezone.now()
    endpoint.last_response_code = res.status_code
    endpoint.last_error = res.error
    if res.ok:
        endpoint.failure_count = 0
        endpoint.save(update_fields=[
            "last_sent_at", 
            "last_response_code", 
            "last_error", 
            "failure_count", 
            "date_last_modified"
        ])
        logger.success(f"Webhook delivered event={event} to {endpoint.target_url} ({res.status_code})")
        return

    # failure path
    endpoint.failure_count = (endpoint.failure_count or 0) + 1
    endpoint.save(update_fields=[
        "last_sent_at", 
        "last_response_code", 
        "last_error", 
        "failure_count", 
        "date_last_modified"
    ])

    # Deactivate 410 Gone permanently
    if res.status_code == 410:
        endpoint.is_active = False
        endpoint.save(update_fields=["is_active", "date_last_modified"])
        logger.warning(f"Webhook endpoint {endpoint_id} returned 410 Gone; deactivated.")
        return

    # Retry with our manual backoff schedule
    idx = min(self.request.retries, len(BACKOFF) - 1)
    countdown = BACKOFF[idx]
    logger.warning(f"Webhook deliver failed; retrying in {countdown}s (attempt {attempt+1}). Err={res.error!r}")
    raise self.retry(
        countdown=countdown, 
        kwargs={
            "endpoint_id": endpoint_id, 
            "event": event, 
            "payload": payload, 
            "attempt": attempt + 1
        }
    )