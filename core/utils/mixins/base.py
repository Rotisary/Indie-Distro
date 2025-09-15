import secrets
from django.db import models
from django.utils import timezone

from core.utils.commons.utils import identifiers


class BaseModelMixin(models.Model):
    date_added = models.DateTimeField(auto_now_add=True)
    date_last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"< {type(self).__name__}({self.id}) >"

    def get_identifier(self):
        return identifiers.ObjectIdentifiers.unique_id