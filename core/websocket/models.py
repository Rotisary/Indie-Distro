from django.db import models
from django.conf import settings


class EventLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="event_logs",
    )
    type = models.CharField(max_length=100)
    entity = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    resource_id = models.CharField(max_length=100, blank=True, null=True)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.entity}:{self.type}:{self.resource_id}"
