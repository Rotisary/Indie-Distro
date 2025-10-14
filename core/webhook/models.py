from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import JSONField

from core.users.models import User
from core.utils.mixins import BaseModelMixin
from core.utils.enums import WebhookEvent
from core.utils.commons.utils import security 


class WebhookEndpoint(BaseModelMixin):
    owner = models.ForeignKey(
        to=User, 
        on_delete=models.CASCADE, 
        related_name="webhook_endpoints", 
        null=True, 
        blank=True,
        verbose_name=_("Webhook Endpoint Owner"),
        help_text=_("The owner of this webhook endpoint, null if global")
    )
    event = models.CharField(
        max_length=64, 
        choices=WebhookEvent.choices(),
        null=False, 
        blank=False,
        verbose_name=_("Webhook Event"),
        help_text=_("The event that triggers this webhook")
    )
    target_url = models.URLField(
        max_length=1024, null=False, blank=False, verbose_name=_("Target URL"),
    )
    secret_encrypted = models.TextField(
        null=False, 
        blank=True, 
        verbose_name=_("Encrypted Secret"),
        help_text=_("Encrypted secret for verification by client")
    )
    is_active = models.BooleanField(default=True)

    headers = JSONField(null=True, blank=True)
    failure_count = models.IntegerField(default=0)
    last_response_code = models.IntegerField(null=True, blank=True)
    last_error = models.TextField(null=True, blank=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)

    def set_secret(self, raw: str):
        self.secret_encrypted = security.encrypt_secret(raw)

    def get_secret(self) -> str:
        return security.decrypt_secret(self.secret_encrypted)

    def __str__(self):
        scope = f"user={self.owner_id}" if self.owner_id else "global"
        return f"{self.event} -> {self.target_url} ({scope})"