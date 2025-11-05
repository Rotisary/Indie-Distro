from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

from .models import Wallet
from core.wallet.tasks import create_wallet_for_user


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_wallet(sender, instance, **kwargs):
    if instance.is_creator and not Wallet.objects.filter(owner=instance).exists():
        transaction.on_commit(lambda: create_wallet_for_user.delay(instance.id, trigger_webhook=True))