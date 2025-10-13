from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Feed, Short
from core.utils.helpers.feed import schedule_release_for_instance


@receiver(post_save, sender=Feed)
def schedule_feed_release(sender, instance: Feed, created, **kwargs):
    # Only schedule if release_date is present and not yet released
    if instance.release_date and not instance.is_released:
        schedule_release_for_instance(instance, "Feed")


@receiver(post_save, sender=Short)
def schedule_short_release(sender, instance: Short, created, **kwargs):
    if instance.release_date and not instance.is_released:
        schedule_release_for_instance(instance, "Short")