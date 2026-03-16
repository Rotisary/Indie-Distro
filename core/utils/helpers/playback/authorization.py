import jwt, datetime

from rest_framework import status
from django.utils import timezone
from django.conf import settings

from core.users.models import User, UserSession
from core.feed.models import Purchase
from core.utils.enums import PurchaseStatusType
from core.utils.exceptions import CustomException


class AccessUtils:
    """
    Class for all utilities that has to do with playback access
    """

    @staticmethod
    def generate_playback_token(owner: int, film: int, purchase: str, session: UserSession | None):
        """
            method to encode user and film data in order to generate token for movie access
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        payload = {
            "sub": str(owner),
            "film_id": str(film),
            "purhase_id": str(purchase),
            "session_id": str(session.id) if session else None,
            # "ip_address": str(session.ip_address),
            # "device": 
            "aud": "stream",
            "nbf": now,
            "exp": now + datetime.timedelta(minutes=10),
            "jti": f"{owner}:{film}:{session.id}" if session else f"{owner}:{film}"
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
        return token
    

    @staticmethod
    def return_playback_token(purchase_id: str, user: User):
        """
            returns the generated token for a verified purchase. To be reused across playback endpoints
        """
        purchase = (
            Purchase.objects
            .select_related("film", "film__file")
            .filter(id=purchase_id, owner=user, status=PurchaseStatusType.ACTIVE.value)
            .first()
        )
        if not purchase:
            raise CustomException(
                message="Permission Denied",
                status_code=status.HTTP_403_FORBIDDEN
            )

        if purchase.expiry_time and purchase.expiry_time <= timezone.now():
            raise CustomException(
                message="Purchase expired",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        
        session = (
            UserSession.objects
            .filter(user=user, is_active=True)
            .order_by("-last_activity")
            .first()
        )
        token = AccessUtils.generate_playback_token(
            user.id, purchase.film.id, purchase_id, session
        )
        return token

    @staticmethod
    def build_playback_url(purchase: Purchase, token: str) -> str:
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
            return f"{master_key}?token={token}"

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

        return f"{base_url}/{master_key}?token={token}"