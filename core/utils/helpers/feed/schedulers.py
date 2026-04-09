from datetime import datetime, time as dt_time
from typing import Optional
from django.utils import timezone
from celery import current_app

from core.feed.tasks import release_object


def schedule_release_for_instance(
    instance,
    model_name: str,
    *,
    when: Optional[datetime] = None,
    previous_release_date=None,
):
    """
    Schedule a release task for an instance (Feed/Short).
    - If 'when' is provided (aware datetime), use it.
    - Else, uses instance.release_date (DateField) at 00:00 in project TZ.
    Skips scheduling if due time is in the past; you may want to process immediately instead.
    """
    if previous_release_date == instance.release_date:
        return None

    if not getattr(instance, "release_date", None):
        if getattr(instance, "release_task_id", None):
            current_app.control.revoke(instance.release_task_id, terminate=False)
            instance.__class__.objects.filter(pk=instance.pk).update(
                release_task_id=None,
                scheduled_release_at=None,
            )
        return None

    if when is None:
        naive = datetime.combine(instance.release_date, dt_time.min)
        when = timezone.make_aware(naive, timezone.get_current_timezone())

    now = timezone.now()
    # Do not schedule if already released
    if getattr(instance, "is_released", None) is True:
        return None

    if getattr(instance, "release_task_id", None):
        current_app.control.revoke(instance.release_task_id, terminate=False)

    if when <= now:
        result = release_object.delay(instance.pk, model_name)
    else:
        result = release_object.apply_async(
            args=(instance.pk, model_name),
            eta=when,
        )

    instance.__class__.objects.filter(pk=instance.pk).update(
        release_task_id=result.id,
        scheduled_release_at=when,
    )
    return result
