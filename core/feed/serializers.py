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
        
    
    class FeedRetrieve(serializers.ModelSerializer):
        owner = BaseUserSerializer()

        class Meta:
            model = Feed
            fields = "__all__"
