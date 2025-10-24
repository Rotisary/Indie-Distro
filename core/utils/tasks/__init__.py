from django.utils import timezone

from celery import shared_task
from django_celery_beat.models import PeriodicTask
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from core.utils.models import IdempotencyKey


@shared_task
def clear_out_periodic_tasks():
    try:
        PeriodicTask.objects.filter(expires__lte=timezone.now()).delete()
    except Exception as e:
        pass


@shared_task
def clear_out_blacklisted_tokens():
    try:
        deleted_count, _ = BlacklistedToken.objects.all().delete()
        print(
            f"[clear_out_blacklisted_tokens] Deleted {deleted_count} blacklisted tokens."
        )
    except Exception as e:
        print(f"[clear_out_blacklisted_tokens] Error: {e}")


@shared_task
def delete_expired_idempotency_keys():
    try:
        deleted_count, details = IdempotencyKey.objects.filter(
            expires_at__lte=timezone.now()
        ).delete()
        print(f"[delete_expired_idempotency_keys] Deleted: {deleted_count} -> {details}")
    except Exception as e:
        print(f"[delete_expired_idempotency_keys] Error: {e}")