from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from unfold.admin import ModelAdmin

from .models import FileModel, FileProcessingJob


@admin.register(FileModel)
class FileModelAdmin(ModelAdmin):
    list_display = ["id", "owner", "file_purpose"]


@admin.register(FileProcessingJob)
class FileProcessingJobModelAdmin(ModelAdmin):
    fieldsets = (
        (
            _("Owner"),
            {
                "classes": ["tab"],
                "fields": ("owner", "file"),
            },
        ),
        (
            _("Meta Information"),
            {
                "classes": ["tab"],
                "fields": (
                    "stages",
                    "metadata",
                    "renditions",
                    "packaging",
                    "thumbnails",
                    "audio",
                    "error"
                ),
            },
        ),
        (
            _("Personal Info"),
            {
                "classes": ["tab"],
                "fields": (
                    "source_key",
                    "source_checksum",
                    "status",
                    "current_stage",
                ),
            },
        ),
        (
            _("Important dates"),
            {
                "classes": ["tab"],
                "fields": ("date_added", "date_last_modified"),
            },
        ),
    )

    list_display = ["file__id", "status", "current_stage"]
    search_fields = ["source_key", "file__id"]
    readonly_fields = ["date_added", "date_last_modified"]
    ordering = ["date_last_modified"]