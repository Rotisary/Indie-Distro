from datetime import datetime, time as dt_time
from django.utils import timezone
from celery import shared_task
from loguru import logger

from .models import Feed, Short
from .views import _get_model_by_name


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def release_object(self, object_id: int, object_model_name: str = None):
    """
    Releases an object (Feed or Short) at due time.
    """
    try:
        model = _get_model_by_name(object_model_name)
        obj = model.objects.filter(pk=object_id).first()

        # If object has is_released, set it; otherwise just log.
        if hasattr(obj, "is_released"):
            if not obj.is_released:
                obj.is_released = True
                obj.save(update_fields=["is_released", "date_last_modified"])
                logger.success(f"Released {object_model_name}({obj.pk})")
            else:
                logger.info(f"{object_model_name}({obj.pk}) already released")
            return "ok"
        
        logger.info(f"{object_model_name}({obj.pk}) has no is_released field")
        return "false"
    except model.DoesNotExist:
        logger.warning(f"release_object_task: missing model {object_model_name} id={object_id}")
        return "missing"
    except Exception as e:
        logger.error(f"release_object_task error for {object_model_name}({object_id}): {e}")
        raise


@shared_task
def reconcile_due_releases():
    """
    Safety net: run periodically to release any objects due in the past
    that may have been missed (e.g., worker down).
    """
    now = timezone.now()

    # For Feed
    due_feeds = Feed.objects.filter(
        is_released=False,
        release_date__isnull=False,
        release_date__lte=now.date(),
    )
    released_count = 0
    for f in due_feeds:
        f.is_released = True
        f.save(update_fields=["is_released", "date_last_modified"])
        released_count += 1

    # For Short
    due_shorts = Short.objects.filter(
        is_released=False,
        release_date__isnull=False,
        release_date__lte=now.date(),
    )
    for s in due_shorts:
        s.is_released = True
        s.save(update_fields=["is_released", "date_last_modified"])
        released_count += 1

    logger.info(f"reconcile_due_releases: released={released_count}")
    return released_count