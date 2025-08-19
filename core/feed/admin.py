from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from .models import Feed


@admin.register(Feed)
class DiscoveryAdmin(ModelAdmin):
    fieldsets = (
        (
            _("Owner"),
            {
                "classes": ["tab"],
                "fields": ("owner",),
            },
        ),
        (
            _("Meta Information"),
            {
                "classes": ["tab"],
                "fields": (
                    "title",
                    "slug",
                    "genre",
                    "type",
                ),
            },
        ),
        (
            _("Personal Info"),
            {
                "classes": ["tab"],
                "fields": (
                    "plot",
                    "cast",
                    "crew",
                    "language",
                    "length",
                    "saved",
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

    list_display = ["owner__first_name", "owner__last_name", "title", "length"]
    search_fields = ["title", "genre", "type"]
    readonly_fields = ["date_added", "date_last_modified"]
    ordering = ["title"]
