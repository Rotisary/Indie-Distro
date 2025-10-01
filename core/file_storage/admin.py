from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from unfold.admin import ModelAdmin

from .models import FileModel, FileProcessingJob


@admin.register(FileModel)
class FileModelAdmin(ModelAdmin):
    fieldsets = (
        (
            _("Owner"),
            {
                "classes": ["tab"],
                "fields": ("owner",),
            },
        ),
        (
            _("Personal Info"),
            {
                "classes": ["tab"],
                "fields": (
                    "film",
                    "file_purpose",
                    "file_key",
                    "mime_type",
                    "checksum"
                ),
            },
        ),
        (
            _("Metadata"),
            {
                "classes": ["tab"],
                "fields": (
                    "file_width",
                    "file_height",
                    "format_name",
                    "has_audio",
                    "hls_master_key",
                    "dash_mpd_key",
                    "last_error"
                ),
            },
        ),
        (
            _("Status"),
            {
                "classes": ["tab"],
                "fields": (
                    "is_verified",
                    "processing_status",
                    "last_processed_at"
                )
            }
        ),
        (
            _("Important dates"),
            {
                "classes": ["tab"],
                "fields": ("date_added", "date_last_modified"),
            },
        ),
    )

    list_display = ["id", "owner__first_name", "file_purpose", "mime_type"]
    search_fields = ["id",]
    readonly_fields = ["date_added", "date_last_modified"]
    ordering = ["date_added"]


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