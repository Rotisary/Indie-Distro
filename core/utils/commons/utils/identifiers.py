import secrets
from django.utils import timezone

class ObjectIdentifiers:

    @staticmethod
    def unique_id():
        return secrets.token_hex(5) + str(int(timezone.now().timestamp()))