import random

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from faker import Faker

from  .mixins import BaseModelMixin
from .enums import KeyProcessStatus
from core.utils.enums import UserAccountType

UserModel = get_user_model()


class User:
    @staticmethod
    def get_random_object(queryset):
        count = queryset.count()
        if count:
            if count == 1:
                return queryset.first()
            else:
                first_id = getattr(queryset.order_by("id").only("id").first(), "id")
                last_id = getattr(queryset.order_by("-id").only("id").first(), "id")
                limiting_id = random.randint(first_id, last_id)
                return queryset.filter(id__gte=limiting_id).order_by("id").first()

    @staticmethod
    def create_random_admin_user(
        type_=UserAccountType.SUPER_ADMINISTRATOR.value, address=None
    ):
        if not address:
            fake = Faker()
            address = fake.email(domain=settings.ORG_EMAIL_DOMAIN)
        return UserModel.objects.create_superuser(
            address, settings.ADMIN_PASSWORD, account_type=type_
        )

    @staticmethod
    def get_random_admin_user(
        address=None,
        type_=UserAccountType.SUPER_ADMINISTRATOR.value,
        seed_on_not_found=False,
    ):
        queryset = UserModel.objects.filter(account_type=type_)
        if address:
            queryset.filter(address=address)
        instance = User.get_random_object(queryset)
        if not instance and seed_on_not_found:
            return User.create_random_admin_user(type_, address=address)
        return instance


class IdempotencyKey(BaseModelMixin):
    key = models.CharField(max_length=128, null=False, blank=False)
    user = models.ForeignKey(
        UserModel, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    request_hash = models.CharField(
        _("Hashed Request Data"),
        max_length=64, 
        blank=False, 
        null=False
    )
    status = models.CharField(
        choices=KeyProcessStatus.choices(),
        max_length=16, 
        default=KeyProcessStatus.IN_PROGRESS.value
    )
    locked_until = models.DateTimeField(null=True, blank=True)
    response_status = models.IntegerField(null=True, blank=True)
    response_body = models.JSONField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = (("key", "user"),)
 
    def is_locked(self):
        return bool(self.locked_until and self.locked_until > timezone.now())