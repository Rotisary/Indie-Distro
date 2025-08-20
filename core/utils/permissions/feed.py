from rest_framework.permissions import BasePermission
from core.utils import enums


class IsFilmOwner(BasePermission):
    """ 
    Allows access only to the owner of the film.
    """
    message: str

    def has_object_permission(self, request, view, obj):
        self.message = "You do not have permission to access this film."
        return obj.owner == request.user


class FilmNotReleased(BasePermission):
    """
    allows action only if the film is not released.
    """
    message: str

    def has_object_permission(self, request, view, obj):
        self.message = "Permission Denied!. "
        return not obj.is_released
