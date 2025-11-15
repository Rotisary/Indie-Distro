import secrets
from django.utils import timezone

class ObjectIdentifiers:

    @staticmethod
    def unique_id():
        return secrets.token_hex(5) + str(int(timezone.now().timestamp()))
    
    @staticmethod
    def unique_hex_id(no_of_bytes=8):
        return secrets.token_hex(no_of_bytes)