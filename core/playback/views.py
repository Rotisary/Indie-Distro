from rest_framework import status, response, views
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.conf import settings
from drf_spectacular.utils import extend_schema

from .serializers import FilmIDSerializer, ShortIDSerializer, PlaybackSerializer
from core.utils.helpers.playback import AccessUtils
from core.utils.helpers.decorators import IdempotencyDecorator
from .throttles import (
    RetrievePlaybackThrottle,
    RefreshPlaybackThrottle,
    RetrieveShortPlaybackThrottle,
    RefreshShortPlaybackThrottle,
)


@extend_schema(tags=["Playback"])
class RetrieveFilmPlaybackURL(views.APIView):
    http_method_names = [
        "post",
    ]
    parser_classes = [
        JSONParser,
    ]
    throttle_classes = [RetrievePlaybackThrottle]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="endpoint to get playback url for cdn",
        request=FilmIDSerializer,
        responses={200: PlaybackSerializer.PlaybackURLRetrieveSerializer},
    )
    @IdempotencyDecorator.make_endpoint_idempotent(ttl=60, namespace="playback_url")
    def post(self, request):
        serializer = FilmIDSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        film_id = serializer.validated_data["film_id"]

        user = request.user
        purchase, cookie_value, expires_at, cookie_path = (
            AccessUtils.return_stream_cookie_for_film(film_id, user)
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
class RefreshFilmPlaybackCookie(views.APIView):
    http_method_names = [
        "post",
    ]
    parser_classes = [
        JSONParser,
    ]
    throttle_classes = [RefreshPlaybackThrottle]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="endpoint to get playback url for cdn",
        request=FilmIDSerializer,
        responses={200: PlaybackSerializer.PlaybackCookieRefreshSerializer},
    )
    @IdempotencyDecorator.make_endpoint_idempotent(ttl=60, namespace="playback_refresh")
    def post(self, request):
        serializer = FilmIDSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        film_id = serializer.validated_data["film_id"]

        user = request.user
        purchase, cookie_value, expires_at, cookie_path = (
            AccessUtils.return_stream_cookie_for_film(film_id, user)
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


@extend_schema(tags=["Playback"])
class RetrieveShortPlaybackURL(views.APIView):
    http_method_names = [
        "post",
    ]
    parser_classes = [
        JSONParser,
    ]
    throttle_classes = [RetrieveShortPlaybackThrottle]
    permission_classes = [AllowAny]

    @extend_schema(
        description="endpoint to get short playback url for cdn",
        request=ShortIDSerializer,
        responses={200: PlaybackSerializer.PlaybackURLRetrieveSerializer},
    )
    @IdempotencyDecorator.make_endpoint_idempotent(
        ttl=60, namespace="short_playback_url"
    )
    def post(self, request):
        serializer = ShortIDSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        short_id = serializer.validated_data["short_id"]

        user = request.user if request.user.is_authenticated else None
        short, cookie_value, expires_at, cookie_path = (
            AccessUtils.return_stream_cookie_for_short(short_id, user)
        )

        playback_url = AccessUtils.build_short_playback_url(short)
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
class RefreshShortPlaybackCookie(views.APIView):
    http_method_names = [
        "post",
    ]
    parser_classes = [
        JSONParser,
    ]
    throttle_classes = [RefreshShortPlaybackThrottle]
    permission_classes = [AllowAny]

    @extend_schema(
        description="endpoint to refresh short playback cookie",
        request=ShortIDSerializer,
        responses={200: PlaybackSerializer.PlaybackCookieRefreshSerializer},
    )
    @IdempotencyDecorator.make_endpoint_idempotent(
        ttl=60, namespace="short_playback_refresh"
    )
    def post(self, request):
        serializer = ShortIDSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        short_id = serializer.validated_data["short_id"]

        user = request.user if request.user.is_authenticated else None
        short, cookie_value, expires_at, cookie_path = (
            AccessUtils.return_stream_cookie_for_short(short_id, user)
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
