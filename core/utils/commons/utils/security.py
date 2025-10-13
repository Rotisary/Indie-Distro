from __future__ import annotations
import base64
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

_fernet: Optional[Fernet] = None

def get_fernet() -> Fernet:
    global _fernet
    if _fernet:
        return _fernet
    key = getattr(settings, "WEBHOOK_ENC_KEY", None)
    if not key:
        raise RuntimeError("WEBHOOK_ENC_KEY not configured")
    
    # Allow raw 32-byte base64 or plain string; normalize to bytes
    if isinstance(key, str):
        key = key.encode("utf-8")
        
    # If not urlsafe-base64, try to base64 it (dev convenience)
    try:
        Fernet(key)  # validate
        _fernet = Fernet(key)
        return _fernet
    except Exception:
        # Try to convert a raw 32-byte string to fernet key
        b32 = base64.urlsafe_b64encode(key)
        _fernet = Fernet(b32)
        return _fernet

def encrypt_secret(raw: str) -> str:
    f = get_fernet()
    token = f.encrypt(raw.encode("utf-8"))
    return token.decode("utf-8")

def decrypt_secret(token: str) -> str:
    f = get_fernet()
    try:
        return f.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        raise RuntimeError("Invalid webhook secret token")