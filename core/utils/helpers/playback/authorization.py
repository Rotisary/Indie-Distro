import base64
import datetime
import hashlib
import hmac
import json

from urllib.parse import urlparse

from rest_framework import status
from django.utils import timezone
from django.conf import settings

from core.users.models import UserSession
from core.feed.models import Purchase, Short
from core.utils.enums import PurchaseStatusType
from core.utils.exceptions import CustomException


class AccessUtils:
    """
    Class for all utilities that has to do with playback access
    """

    @staticmethod
    def _b64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    @staticmethod
    def _build_stream_cookie_path(master_key: str) -> str:
        if master_key.startswith("http://") or master_key.startswith("https://"):
            path = urlparse(master_key).path
        else:
            path = f"/{master_key.lstrip('/')}"

        if "/" not in path.strip("/"):
            return "/"

        return path.rsplit("/", 1)[0] + "/"

    @staticmethod
    def generate_stream_cookie(purchase: Purchase, session: UserSession | None):
        ttl_seconds = int(getattr(settings, "STREAM_COOKIE_TTL_SECONDS", 900))
        now = datetime.datetime.now(datetime.timezone.utc)
        expires_at = now + datetime.timedelta(seconds=ttl_seconds)

        file = getattr(purchase.film, "file", None)
        master_key = file and (file.hls_master_key or "")
        if not master_key:
            raise CustomException(
                message="Playback not available yet",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        cookie_path = AccessUtils._build_stream_cookie_path(master_key)
        payload = {
            "sub": str(purchase.owner_id),
            "film_id": str(purchase.film_id),
            "purchase_id": str(purchase.id),
            "session_id": str(session.id) if session else None,
            "path": cookie_path,
            "exp": int(expires_at.timestamp()),
        }

        payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        payload_b64 = AccessUtils._b64url_encode(payload_json)
        secret = getattr(settings, "STREAM_COOKIE_SECRET", "")
        if not secret:
            raise CustomException(
                message="Stream cookie secret not configured",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        signature = hmac.new(
            secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256
        ).digest()
        signature_b64 = AccessUtils._b64url_encode(signature)
        cookie_value = f"{payload_b64}.{signature_b64}"
        return cookie_value, expires_at, cookie_path

    @staticmethod
    def generate_short_stream_cookie(short: Short, session: UserSession | None):
        ttl_seconds = int(getattr(settings, "STREAM_COOKIE_TTL_SECONDS", 900))
        now = datetime.datetime.now(datetime.timezone.utc)
        expires_at = now + datetime.timedelta(seconds=ttl_seconds)

        file = getattr(short, "file", None)
        master_key = file and (file.hls_master_key or "")
        if not master_key:
            raise CustomException(
                message="Playback not available yet",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        cookie_path = AccessUtils._build_stream_cookie_path(master_key)
        payload = {
            "sub": str(short.owner_id),
            "short_id": str(short.id),
            "session_id": str(session.id) if session else None,
            "path": cookie_path,
            "aud": "shorts",
            "exp": int(expires_at.timestamp()),
        }

        payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        payload_b64 = AccessUtils._b64url_encode(payload_json)
        secret = getattr(settings, "STREAM_COOKIE_SECRET", "")
        if not secret:
            raise CustomException(
                message="Stream cookie secret not configured",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        signature = hmac.new(
            secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256
        ).digest()
        signature_b64 = AccessUtils._b64url_encode(signature)
        cookie_value = f"{payload_b64}.{signature_b64}"
        return cookie_value, expires_at, cookie_path

    @staticmethod
    def get_valid_purchase_for_film(film_id: int, user) -> Purchase:
        purchase = (
            Purchase.objects.select_related("film", "film__file")
            .filter(
                film_id=film_id,
                owner=user,
                status=PurchaseStatusType.ACTIVE.value,
            )
            .first()
        )
        if not purchase:
            raise CustomException(
                message="Permission Denied",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        if purchase.expiry_time and purchase.expiry_time <= timezone.now():
            raise CustomException(
                message="Purchase expired",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return purchase

    @staticmethod
    def return_stream_cookie(film_id: int, user):
        purchase = AccessUtils.get_valid_purchase_for_film(film_id, user)
        session = (
            UserSession.objects.filter(user=user, is_active=True)
            .order_by("-last_activity")
            .first()
        )
        cookie_value, expires_at, cookie_path = AccessUtils.generate_stream_cookie(
            purchase, session
        )
        return purchase, cookie_value, expires_at, cookie_path

    @staticmethod
    def return_stream_cookie_for_film(film_id: int, user):
        purchase = AccessUtils.get_valid_purchase_for_film(film_id, user)
        session = (
            UserSession.objects.filter(user=user, is_active=True)
            .order_by("-last_activity")
            .first()
        )
        cookie_value, expires_at, cookie_path = AccessUtils.generate_stream_cookie(
            purchase, session
        )
        return purchase, cookie_value, expires_at, cookie_path

    @staticmethod
    def return_stream_cookie_for_short(short_id: int, user):
        short = (
            Short.objects.select_related("file")
            .filter(id=short_id, is_released=True)
            .first()
        )
        if not short:
            raise CustomException(
                message="Short not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        session = None
        if user:
            session = (
                UserSession.objects.filter(user=user, is_active=True)
                .order_by("-last_activity")
                .first()
            )
        cookie_value, expires_at, cookie_path = (
            AccessUtils.generate_short_stream_cookie(short, session)
        )
        return short, cookie_value, expires_at, cookie_path

    @staticmethod
    def build_playback_url(purchase: Purchase) -> str:
        """
        Builds a streamable HLS URL for a purchased film.
        """
        file = getattr(purchase.film, "file", None)
        master_key = file and (file.hls_master_key or "")
        if not master_key:
            raise CustomException(
                message="Playback not available yet",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if master_key.startswith("http://") or master_key.startswith("https://"):
            return master_key

        base_url = (getattr(settings, "STREAM_BASE_URL", "") or "").rstrip("/")
        if not base_url and getattr(settings, "USING_MANAGED_STORAGE", False):
            domain = getattr(settings, "AWS_S3_CUSTOM_DOMAIN", "")
            if domain:
                base_url = f"https://{domain}".rstrip("/")

        if not base_url:
            raise CustomException(
                message="Streaming base URL not configured",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return f"{base_url}/{master_key}"

    @staticmethod
    def build_short_playback_url(short: Short) -> str:
        file = getattr(short, "file", None)
        master_key = file and (file.hls_master_key or "")
        if not master_key:
            raise CustomException(
                message="Playback not available yet",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if master_key.startswith("http://") or master_key.startswith("https://"):
            return master_key

        base_url = (getattr(settings, "STREAM_BASE_URL", "") or "").rstrip("/")
        if not base_url and getattr(settings, "USING_MANAGED_STORAGE", False):
            domain = getattr(settings, "AWS_S3_CUSTOM_DOMAIN", "")
            if domain:
                base_url = f"https://{domain}".rstrip("/")

        if not base_url:
            raise CustomException(
                message="Streaming base URL not configured",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return f"{base_url}/{master_key}"
