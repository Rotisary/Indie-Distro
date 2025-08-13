from rest_framework.permissions import BasePermission
from core.utils import enums


class IsGuestUser(BasePermission):
    """
    Allows access only to non-authenticated accounts.
    """

    message: str

    def has_permission(self, request, view):
        self.message = "You are already logged in"
        return not request.user.is_authenticated