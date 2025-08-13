from .base import BaseEnum


class UserAccountType(BaseEnum):

    SUPER_ADMINISTRATOR = "super_administrator"
    STAFF = "staff"
    USER = "site_user"


class UserGenderType(BaseEnum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"