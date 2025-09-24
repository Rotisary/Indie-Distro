import datetime

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from core.users.serializers import BaseUserSerializer
from core.feed.serializers import FeedSerializer
from core.utils.enums import FilePurposeType
from .models import FileModel



class FileSerializer:
    class Create(serializers.ModelSerializer):
        class Meta:
            model = FileModel
            exclude = [
                "currently_under_processing",
                "is_verified",
                "file_key"
            ]
    
          
    class ListRetrieve(serializers.ModelSerializer):
        owner = BaseUserSerializer()
        film =  FeedSerializer.FeedRetrieve()

        class Meta:
            model = FileModel
            fields = "__all__"


class SignedURLRequestSerializer(serializers.Serializer):
    file_name = serializers.CharField(required=True)
    purpose = serializers.ChoiceField(
        choices=FilePurposeType.choices(), required=True
    )