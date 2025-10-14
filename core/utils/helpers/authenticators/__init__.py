from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication
from core.utils import enums
from core.utils.models import User


class ServerAuthentication(BaseAuthentication):
    def authenticate(self, request):
        secret_key = request.META.get(f"HTTP_{settings.SERVER_SECRET_KEY_FIELD_NAME}")

        if not secret_key:
            msg = _('Provide a valid "secret-key" in your request authorization header')
            raise exceptions.AuthenticationFailed(msg)
        elif secret_key != settings.SERVER_SECRET_KEY:
            msg = _("Invalid secret-key provided")
            raise exceptions.AuthenticationFailed(msg)
        return (
            User.get_random_admin_user(
                address=getattr(settings, "ADMIN_EMAIL", None),
                type_=enums.UserAccountType.SUPER_ADMINISTRATOR.value,
                seed_on_not_found=True,
            ),
            None,
        )