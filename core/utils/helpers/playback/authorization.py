import jwt, datetime

from rest_framework import status
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
    def generate_playback_token(owner: int, film: int, purchase: str, session: UserSession):
        """
            method to encode user and film data in order to generate token for movie access
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        payload = {
            "sub": str(owner),
            "film_id": str(film),
            "purhase_id": str(purchase),
            "session_id": str(session.id),
            # "ip_address": str(session.ip_address),
            # "device": 
            "aud": "stream",
            "nbf": now,
            "exp": now + datetime.timedelta(minutes=10),
            "jti": f"{owner}:{film}:{session.id}"
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
        return token
    

    @staticmethod
    def return_playback_token(purchase_id: str, user: User):
        """
            returns the generated token for a verified purchase. To be reused across playback endpoints
        """
        purchase = Purchase.objects.filter(
            id=purchase_id, owner=user, status=PurchaseStatusType.ACTIVE.value
        ).first()
        if not purchase:
            raise CustomException(
                message="Permission Denied",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        token = AccessUtils.generate_playback_token(
            user.id, purchase.film.id, purchase_id, user.usersession
        )
        return token