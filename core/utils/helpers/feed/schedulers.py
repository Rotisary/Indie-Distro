from datetime import datetime, time as dt_time
from typing import Optional
from django.utils import timezone

from core.feed.tasks import release_object


def schedule_release_for_instance(instance, model_name: str, *, when: Optional[datetime] = None):
    """
    Schedule a release task for an instance (Feed/Short).
    - If 'when' is provided (aware datetime), use it.
    - Else, uses instance.release_date (DateField) at 00:00 in project TZ.
    Skips scheduling if due time is in the past; you may want to process immediately instead.
    """
    if when is None:
        if getattr(instance, "release_date", None):

            naive = datetime.combine(instance.release_date, dt_time.min)
            when = timezone.make_aware(naive, timezone.get_current_timezone())
        else:
            return None

    now = timezone.now()
    # Do not schedule if already released
    if getattr(instance, "is_released", None) is True:
        return None

    if when <= now:
        return release_object.delay(
            instance.pk, model_name
        )

    # Schedule with ETA (precise run_at)
    return release_object.apply_async(
        args=(instance.pk, model_name),
        eta=when,
    )