from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from core.utils.enums.base import ModelNameChoice


class Bookmark(serializers.Serializer):
    id = serializers.CharField(
        required=True, write_only=True, help_text=_("id of object to be bookmarked")
    )
    model_name = serializers.ChoiceField(
        choices=ModelNameChoice.choices(),
        required=True, 
        write_only=True, 
        help_text=_("type of object to be bookmarked e.g Film, Short")
    )
