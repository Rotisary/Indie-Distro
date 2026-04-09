from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from core.utils.helpers.feed import schedule_release_for_instance

from .models import Feed, Short


@receiver(post_save, sender=Feed)
def schedule_feed_release(sender, instance: Feed, created, **kwargs):
    previous = getattr(instance, "_previous_release_date", None)
    if instance.is_released:
        return

    if previous == instance.release_date:
        return

    # Schedule or clear based on updated release_date
    if instance.release_date or previous:
        schedule_release_for_instance(
            instance,
            "Feed",
            previous_release_date=previous,
        )


@receiver(post_save, sender=Short)
def schedule_short_release(sender, instance: Short, created, **kwargs):
    previous = getattr(instance, "_previous_release_date", None)
    if instance.is_released:
        return

    if previous == instance.release_date:
        return

    if instance.release_date or previous:
        schedule_release_for_instance(
            instance,
            "Short",
            previous_release_date=previous,
        )


@receiver(pre_save, sender=Feed)
def capture_feed_release_date(sender, instance: Feed, **kwargs):
    if not instance.pk:
        instance._previous_release_date = None
        return

    previous = (
        sender.objects.filter(pk=instance.pk)
        .values_list("release_date", flat=True)
        .first()
    )
    instance._previous_release_date = previous


@receiver(pre_save, sender=Short)
def capture_short_release_date(sender, instance: Short, **kwargs):
    if not instance.pk:
        instance._previous_release_date = None
        return

    previous = (
        sender.objects.filter(pk=instance.pk)
        .values_list("release_date", flat=True)
        .first()
    )
    instance._previous_release_date = previous
