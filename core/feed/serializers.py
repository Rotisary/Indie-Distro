import datetime

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from core.users.serializers import BaseUserSerializer
from .models import Feed, Short
from core.file_storage.models import FileModel


class BaseFilmSerializer(serializers.ModelSerializer):

    class Meta:
        model = Feed
        fields = [
            "id",
            "title",
            "plot",
            "release_date",
            "duration",
            "genre",
            "type"
        ]


class FeedSerializer:
    class FeedCreate(serializers.ModelSerializer):
        class Meta:
            model = Feed
            exclude = [
                "slug",
                "saved",
                "is_released",
                "date_added",
                "date_last_modified"
            ]
        

        def validate_cast(self, value):
            if len(value) > 5:
                raise serializers.ValidationError("Cannot have more than 5 major actors.")
            return value
        

        def validate_crew(self, value):
            if len(value) > 5:
                raise serializers.ValidationError("Cannot have more than 5 crew members.")
            return value
        
        def validate_release_date(self, value):
            if value and value <= datetime.date.today():
                raise serializers.ValidationError(
                    "Release date cannot be today. Please set a date later than today."
                )
            return value
        
    
    class FeedRetrieve(serializers.ModelSerializer):
        owner = BaseUserSerializer()

        class Meta:
            model = Feed
            exclude = ["saved", "date_last_modified"]

    
class ShortSerializer:
    class ShortCreate(serializers.ModelSerializer):
        class Meta:
            model = Short
            exclude = [
                "slug",
                "saved",
                "views_count",
                "likes_count",
                "comments_count",
                "is_released",
                "date_added",
                "date_last_modified",
            ]

        def validate_release_date(self, value):
            if value and value <= datetime.date.today():
                raise serializers.ValidationError(
                    "Release date cannot be today. Please set a date later than today."
                )
            return value

        def validate_file(self, value: FileModel):
            request = self.context.get("request")
            if request and value.owner.id != request.user.id:
                raise serializers.ValidationError("You do not own the provided file.")
            return value

        def validate_film(self, value):
            request = self.context.get("request")
            if request and value and value.owner.id != request.user.id:
                raise serializers.ValidationError("You do not own the provided film.")
            return value

    class Retrieve(serializers.ModelSerializer):
        owner = BaseUserSerializer()
        film = BaseFilmSerializer()

        class Meta:
            model = Short
            exclude = ["saved", "date_last_modified"]

