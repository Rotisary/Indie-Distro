import datetime

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from core.users.serializers import BaseUserSerializer
from core.feed.serializers import FeedSerializer
from core.utils.enums import FilePurposeType
from .models import FileModel



class FileSerializer:
    class FileCreate(serializers.ModelSerializer):
        class Meta:
            model = FileModel
            exclude = [
                "processing_status",
                "is_verified",
                "file_key"
            ]
    
          
    class ListRetrieve(serializers.ModelSerializer):
        owner = BaseUserSerializer()
        film =  FeedSerializer.FeedRetrieve()

        class Meta:
            model = FileModel
            fields = "__all__"


class SignedURLSerializer:
    class SignedURLRequestSerializer(serializers.Serializer):
        file_name = serializers.CharField(required=True)
        purpose = serializers.ChoiceField(
            choices=FilePurposeType.choices(), required=True
        )
    
    class SignedURLResponseSerializer(serializers.Serializer):
        file_id = serializers.CharField(read_only=True)
        signed_url = serializers.CharField(read_only=True)


class FileProcessingJobPollSerializer(serializers.Serializer):
    status = serializers.CharField(read_only=True)
    owner = serializers.IntegerField(read_only=True)
    file = serializers.DictField(
        read_only=True,
        help_text=_(
            "contains the details of the file associated with the job(id, name, purpose, key)"
        )
    )
        