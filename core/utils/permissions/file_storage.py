from rest_framework.permissions import BasePermission


class FileMediaNotReleased(BasePermission):
    """
    Allows deletion only if linked film/short is not released.
    """

    message: str

    def has_object_permission(self, request, view, obj):
        self.message = "Permission Denied!."
        film = getattr(obj, "film", None)
        short = getattr(obj, "short", None)
        film_released = bool(film and getattr(film, "is_released", False))
        short_released = bool(short and getattr(short, "is_released", False))
        return not (film_released or short_released)
