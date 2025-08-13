from django.urls import path
from .views import (
    CreateUser,
    Login,
    Logout,
    TokenRefresh
)

urlpatterns = [
    path("users/", CreateUser.as_view(), name="create-user"),
    path("auth/login/", Login.as_view(), name="login"),
    path("auth/logout/", Logout.as_view(), name="logout"),
    path("auth/token/refresh/", TokenRefresh.as_view(), name="token-refresh"),
]