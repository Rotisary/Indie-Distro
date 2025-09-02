import jwt, datetime
from django.conf import settings
from core.users.models import UserSession


class AccessUtils:
    """
    Class for all utilities that has to do with playback access
    """

    @staticmethod
    def generate_playback_token(owner: int, film: int, purchase: str, session: UserSession):
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