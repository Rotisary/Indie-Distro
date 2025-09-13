import os, uuid

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from core.utils.mixins import BaseModelMixin
from core.utils import enums
from core.users.models import User
from core.feed.models import Feed


class FileModel(BaseModelMixin):
    id = models.CharField(
        primary_key=True,
        blank=True, 
        null=False, 
        unique=True, 
        max_length=100
    )
    owner = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        verbose_name=_("File Owner")
    )
    film = models.ForeignKey(
        to=Feed,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("File Film"),
        help_text=_("The film related to the file")
    )
    file_purpose = models.CharField(
        choices=enums.FilePurposeType.choices(),
        null=False,
        blank=False,
        verbose_name=_("File purpose"),
        max_length=100
    )
    file = models.FileField(
        _("Content"),
        upload_to="uploads/%Y/%m/%d/", 
        null=False, 
        blank=False
    )
    mime_type = models.CharField(
        _("File MIME Type"),
        null=True,
        blank=True,
        max_length=100,
    )
    is_verified = models.BooleanField(
        _("Is this file verified"),
        null=False,
        blank=True,
        default=False,
        editable=True,
    )
    upload_session_id = models.CharField(
        _("File Upload Session ID"),
        null=False,
        editable=False,
        default=uuid.uuid4,
        max_length=64,
    )
    currently_under_processing = models.BooleanField(
        _("Is this file currently under processing"),
        null=False,
        blank=True,
        default=True,
    )
    original_filename = models.CharField(
        _("Original File Name"),
        null=True,
        blank=True,
        max_length=500,
        editable=False,
    )

    class Meta:
        verbose_name = _("File")
        verbose_name_plural = _("Files")


    @property
    def file_type(self):
        mimetype = self.mime_type
        return mimetype and mimetype.split("/")[0]
    
    
    @property
    def file_src(self):
        return (
            self.file.url
            if settings.USING_MANAGED_STORAGE
            else os.path.join(settings.BASE_DIR, self.file.path)
        )
    

    def __str__(self):
        return self.id
    

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = self.get_identifier()
        super().save(*args, **kwargs)
