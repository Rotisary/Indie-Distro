from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import FileModel


@admin.register(FileModel)
class FileModelAdmin(ModelAdmin):
    list_display = ["id", "owner", "purpose"]
