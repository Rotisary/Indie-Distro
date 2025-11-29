from rest_framework import serializers
from django.utils.translation import gettext_lazy as _


class PurchaseIDSerializer(serializers.Serializer):
    purchase_id = serializers.UUIDField(required=True, write_only=True)


class PlaybackSerializer:
    class PlaybackURLRetrieveSerializer(serializers.Serializer):
        url = serializers.CharField(read_only=True)
    
    class PlaybackTokenRefreshSerializer(serializers.Serializer):
        token = serializers.CharField(read_only=True)