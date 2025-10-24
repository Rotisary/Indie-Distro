from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from .models import Feed, Purchase, Short


@admin.register(Feed)
class FeedAdmin(ModelAdmin):
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
                    "sale_type"
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
                    "duration",
                    "price",
                    "rental_duration",
                    "is_released",
                    "saved",
                ),
            },
        ),
        (
            _("Important dates"),
            {
                "classes": ["tab"],
                "fields": ("release_date", "date_added", "date_last_modified"),
            },
        ),
    )

    list_display = ["owner__first_name", "owner__last_name", "title", "duration", "price"]
    search_fields = ["title", "genre", "type", "sale_type"]
    readonly_fields = ["date_added", "date_last_modified"]
    ordering = ["title"]


@admin.register(Purchase)
class PurchaseAdmin(ModelAdmin):
    fieldsets = (
        (
            _("Owner"),
            {
                "classes": ["tab"],
                "fields": (
                    "owner",
                    "film"
                ),
            },
        ),
        (
            _("Personal Info"),
            {
                "classes": ["tab"],
                "fields": (
                    "id",
                    "status",
                    "expiry_time",
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

    list_display = ["id", "film__id", "owner__first_name", "status"]
    search_fields = [
        "owner__first_name", 
        "owner__last_name",
        "film__name"
    ]
    readonly_fields = ["date_added", "date_last_modified"]
    ordering = ["-date_added"]


@admin.register(Short)
class ShortAdmin(ModelAdmin):
    fieldsets = (
        (
            _("Owner"),
            {
                "classes": ["tab"],
                "fields": ("owner", "film", "file"),
            },
        ),
        (
            _("Meta Information"),
            {
                "classes": ["tab"],
                "fields": (
                    "slug",
                    "type",
                ),
            },
        ),
        (
            _("Personal Info"),
            {
                "classes": ["tab"],
                "fields": (
                    "caption",
                    "language",
                    "duration",
                    "tags",
                    "is_released",
                    "saved",
                ),
            },
        ),
        (
            _("Analytics Info"),
            {
                "classes": ["tab"],
                "fields": (
                    "views_count",
                    "likes_count",
                    "comments_count",
                ),
            },
        ),
        (
            _("Important dates"),
            {
                "classes": ["tab"],
                "fields": ("release_date", "date_added", "date_last_modified"),
            },
        ),
    )

    list_display = ["owner__first_name", "owner__last_name", "release_date"]
    search_fields = ["slug", "owner__email", "film__title"]
    readonly_fields = ["date_added", "date_last_modified"]
    ordering = ["-date_added"]