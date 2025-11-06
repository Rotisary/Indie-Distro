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
    

class IsAccountType:
    class SuperAdminUser(BasePermission):
        """
        Allows access only to super admin users.
        """

        message: str

        def has_permission(self, request, view):
            self.message = "This endpoint is only for super admins"
            return (
                request.user.account_type
                == enums.UserAccountType.SUPER_ADMINISTRATOR.value
            )

    class AdminUser(BasePermission):
        """
        Allows access only to admin users.
        """

        message: str

        def has_permission(self, request, view):
            self.message = "You are not an admin!"
            return request.user.account_type in [
                enums.UserAccountType.STAFF.value,
                enums.UserAccountType.SUPER_ADMINISTRATOR.value,
            ]

    class IsCreatorAccount(BasePermission):
        """
        Allows access only to creators.
        """

        message: str

        def has_permission(self, request, view):
            self.message = "You are not a creator!"
            return (
                request.user.account_type == enums.UserAccountType.USER.value
                and request.user.is_creator
            )

         
    class IsAdminOrCreator(BasePermission):
        def has_permission(self, request, view):
            return (
                IsAccountType.AdminUser().has_permission(request, view)
                or IsAccountType.IsCreatorAccount().has_permission(request, view)
            )
        

class IsObjOwner(BaseException):
    """
    Allows access only to the owner of an object.
    """  
    message: str

    def has_object_permissions(self, request, view, obj):
        self.message = "You do not have permission to access this object."
        return obj.owner == request.user
    