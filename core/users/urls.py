from django.urls import path
from .views import (
    CreateUser,
    RetrieveUpdateUser,
    BecomeCreator,
    Login,
    Logout,
    TokenRefresh
)

urlpatterns = [
    path("users/", CreateUser.as_view(), name="create-user"),
    path("users/me/", RetrieveUpdateUser.as_view(), name="retrieve-update-user"),
    path("users/me/become-creator/", BecomeCreator.as_view(), name="become-creator"),
    path("auth/login/", Login.as_view(), name="login"),
    path("auth/logout/", Logout.as_view(), name="logout"),
    path("auth/token/refresh/", TokenRefresh.as_view(), name="token-refresh"),
]