from rest_framework import status, response, views
from rest_framework.parsers import JSONParser
from django.conf import settings
from drf_spectacular.utils import extend_schema

from .serializers import PurchaseIDSerializer, PlaybackSerializer
from core.utils.helpers.playback import AccessUtils


@extend_schema(tags=["Playback"])
class RetrievePlaybackURL(views.APIView):
    http_method_names = ["post", ]
    parser_classes = [JSONParser, ]


    @extend_schema(
        description="endpoint to get playback url for cdn",
        request=PurchaseIDSerializer,
        responses={200: PlaybackSerializer.PlaybackURLRetrieveSerializer}
    )
    def post(self, request):
        serializer = PurchaseIDSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        purchase_id = serializer.validated_data["purchase_id"]

        user = request.user
        purchase, cookie_value, expires_at, cookie_path = AccessUtils.return_stream_cookie(
            purchase_id, user
        )

        playback_url = AccessUtils.build_playback_url(purchase)
        cookie_name = getattr(settings, "STREAM_COOKIE_NAME", "stream_auth")
        cookie_domain = getattr(settings, "STREAM_COOKIE_DOMAIN", None)
        cookie_ttl = int(getattr(settings, "STREAM_COOKIE_TTL_SECONDS", 900))
        cookie_secure = bool(getattr(settings, "STREAM_COOKIE_SECURE", True))
        cookie_samesite = getattr(settings, "STREAM_COOKIE_SAMESITE", "None")

        resp = response.Response(
            data={"url": playback_url, "expires_at": expires_at},
            status=status.HTTP_200_OK,
        )
        resp.set_cookie(
            cookie_name,
            cookie_value,
            max_age=cookie_ttl,
            expires=expires_at,
            domain=cookie_domain,
            path=cookie_path,
            secure=cookie_secure,
            httponly=True,
            samesite=cookie_samesite,
        )
        return resp
    

@extend_schema(tags=["Playback"])
class RefreshPlaybackToken(views.APIView):
    http_method_names = ["post", ]
    parser_classes = [JSONParser, ]


    @extend_schema(
        description="endpoint to get playback url for cdn",
        request=PurchaseIDSerializer,
        responses={200: PlaybackSerializer.PlaybackTokenRefreshSerializer}
    )
    def post(self, request):
        serializer = PurchaseIDSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        purchase_id = serializer.validated_data["purchase_id"]

        user = request.user
        purchase, cookie_value, expires_at, cookie_path = AccessUtils.return_stream_cookie(
            purchase_id, user
        )

        cookie_name = getattr(settings, "STREAM_COOKIE_NAME", "stream_auth")
        cookie_domain = getattr(settings, "STREAM_COOKIE_DOMAIN", None)
        cookie_ttl = int(getattr(settings, "STREAM_COOKIE_TTL_SECONDS", 900))
        cookie_secure = bool(getattr(settings, "STREAM_COOKIE_SECURE", True))
        cookie_samesite = getattr(settings, "STREAM_COOKIE_SAMESITE", "None")

        resp = response.Response(
            data={"expires_at": expires_at}, status=status.HTTP_200_OK
        )
        resp.set_cookie(
            cookie_name,
            cookie_value,
            max_age=cookie_ttl,
            expires=expires_at,
            domain=cookie_domain,
            path=cookie_path,
            secure=cookie_secure,
            httponly=True,
            samesite=cookie_samesite,
        )
        return resp