import datetime

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from core.users.serializers import BaseUserSerializer
from .models import Feed



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

    class Bookmark(serializers.Serializer):
        id = serializers.PrimaryKeyRelatedField(queryset=Feed.objects.all())
