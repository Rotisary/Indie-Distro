
from rest_framework import serializers

from core.feed.serializers import FeedSerializer
from core.users.serializers import BaseUserSerializer
from core.utils.enums import FilePurposeType

from .models import FileModel


class FileSerializer:
    class FileCreate(serializers.ModelSerializer):
        class Meta:
            model = FileModel
            exclude = [
                "processing_status",
                "last_processed_at",
                "is_verified",
                "file_key",
                "hls_master_key",
                "dash_mpd_key",
                "has_audio",
                "last_error",
            ]

    class ListRetrieve(serializers.ModelSerializer):
        owner = BaseUserSerializer()
        film = FeedSerializer.FeedRetrieve()

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
