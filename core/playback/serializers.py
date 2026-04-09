from rest_framework import serializers


class FilmIDSerializer(serializers.Serializer):
    film_id = serializers.IntegerField(required=True, write_only=True)


class ShortIDSerializer(serializers.Serializer):
    short_id = serializers.IntegerField(required=True, write_only=True)


class PlaybackSerializer:
    class PlaybackURLRetrieveSerializer(serializers.Serializer):
        url = serializers.CharField(read_only=True)
        expires_at = serializers.DateTimeField(read_only=True)

    class PlaybackCookieRefreshSerializer(serializers.Serializer):
        expires_at = serializers.DateTimeField(read_only=True)
