import uuid

from django.urls import reverse

import pytest
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.test import APIClient

from core.users import views as user_views
from core.users.models import User
from core.users.tests.factories.user_factories import (
    DEFAULT_PASSWORD,
    UserFactory,
    UserSessionFactory,
)

pytestmark = pytest.mark.django_db


def build_create_user_payload():
    unique = uuid.uuid4().hex
    return {
        "email": f"user{unique}@example.com",
        "first_name": "Test",
        "last_name": "User",
        "username": f"user_{unique}",
        "location": "Lagos, NG",
        "password": DEFAULT_PASSWORD,
        "password2": DEFAULT_PASSWORD,
    }


def build_update_payload():
    unique = uuid.uuid4().hex
    return {
        "first_name": "Updated",
        "last_name": "User",
        "username": f"updated_{unique}",
        "is_email_verified": True,
        "bio": "Updated bio",
        "gender": "Male",
        "is_banned": False,
        "location": "Abuja, NG",
    }


CREATE_USER_URL = reverse("create-user")
ME_URL = reverse("retrieve-update-user")
BECOME_CREATOR_URL = reverse("become-creator")
LOGIN_URL = reverse("login")
LOGOUT_URL = reverse("logout")
TOKEN_REFRESH_URL = reverse("token-refresh")


def test_create_user_success(anonymous_client, server_auth_headers, admin_user):
    payload = build_create_user_payload()

    response = anonymous_client.post(
        CREATE_USER_URL, payload, format="json", **server_auth_headers
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["user"]["email"] == payload["email"]
    assert "token" in response.data
    assert User.objects.filter(email=payload["email"]).exists()


def test_create_user_unauthorized(anonymous_client):
    response = anonymous_client.post(
        CREATE_USER_URL, build_create_user_payload(), format="json"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_user_forbidden(monkeypatch, user):
    monkeypatch.setattr(user_views.CreateUser, "permission_classes", [IsAdminUser])

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(CREATE_USER_URL, build_create_user_payload(), format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_user_invalid_payload(anonymous_client, server_auth_headers, admin_user):
    payload = build_create_user_payload()
    payload["password2"] = "Mismatch123!"

    response = anonymous_client.post(
        CREATE_USER_URL, payload, format="json", **server_auth_headers
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_create_user_missing_required_fields(
    anonymous_client, server_auth_headers, admin_user
):
    response = anonymous_client.post(
        CREATE_USER_URL, {"password": DEFAULT_PASSWORD}, format="json", **server_auth_headers
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_create_user_not_found(anonymous_client, server_auth_headers, admin_user):
    response = anonymous_client.post(
        "/api/users/unknown/",
        build_create_user_payload(),
        format="json",
        **server_auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_login_success(anonymous_client, server_auth_headers, admin_user):
    user = UserFactory()
    payload = {"email": user.email, "password": DEFAULT_PASSWORD}

    response = anonymous_client.post(
        LOGIN_URL, payload, format="json", **server_auth_headers
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["user"]["email"] == user.email
    assert "token" in response.data


def test_login_unauthorized(anonymous_client):
    user = UserFactory()
    response = anonymous_client.post(
        LOGIN_URL, {"email": user.email, "password": DEFAULT_PASSWORD}, format="json"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_login_forbidden(monkeypatch, user):
    monkeypatch.setattr(user_views.Login, "permission_classes", [IsAdminUser])

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        LOGIN_URL, {"email": user.email, "password": DEFAULT_PASSWORD}, format="json"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_login_invalid_payload(anonymous_client, server_auth_headers, admin_user):
    response = anonymous_client.post(
        LOGIN_URL, {"email": "not-an-email", "password": DEFAULT_PASSWORD}, format="json", **server_auth_headers
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_login_missing_required_fields(anonymous_client, server_auth_headers, admin_user):
    response = anonymous_client.post(LOGIN_URL, {}, format="json", **server_auth_headers)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_login_not_found(anonymous_client, server_auth_headers, admin_user):
    response = anonymous_client.post(
        "/api/auth/login/unknown/",
        {"email": "user@example.com", "password": DEFAULT_PASSWORD},
        format="json",
        **server_auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_token_refresh_success(anonymous_client, server_auth_headers, admin_user):
    user = UserFactory()
    token = user.retrieve_auth_token()
    UserSessionFactory(user=user, refresh=token["refresh"], access=token["access"])

    response = anonymous_client.post(
        TOKEN_REFRESH_URL, {"refresh": token["refresh"]}, format="json", **server_auth_headers
    )

    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert "refresh" in response.data


def test_token_refresh_unauthorized(anonymous_client):
    user = UserFactory()
    token = user.retrieve_auth_token()

    response = anonymous_client.post(
        TOKEN_REFRESH_URL, {"refresh": token["refresh"]}, format="json"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_token_refresh_forbidden(monkeypatch, user):
    monkeypatch.setattr(user_views.TokenRefresh, "permission_classes", [IsAdminUser])

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        TOKEN_REFRESH_URL, {"refresh": "invalid"}, format="json"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_token_refresh_invalid_payload(anonymous_client, server_auth_headers, admin_user):
    user = UserFactory()
    token = user.retrieve_auth_token()

    response = anonymous_client.post(
        TOKEN_REFRESH_URL, {"refresh": token["refresh"]}, format="json", **server_auth_headers
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_token_refresh_missing_required_fields(
    anonymous_client, server_auth_headers, admin_user
):
    response = anonymous_client.post(
        TOKEN_REFRESH_URL, {}, format="json", **server_auth_headers
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_token_refresh_not_found(anonymous_client, server_auth_headers, admin_user):
    response = anonymous_client.post(
        "/api/auth/token/refresh/unknown/",
        {"refresh": "invalid"},
        format="json",
        **server_auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_retrieve_user_success(authenticated_client, user):
    response = authenticated_client.get(ME_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["email"] == user.email


def test_retrieve_user_unauthorized(anonymous_client):
    response = anonymous_client.get(ME_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_retrieve_user_forbidden(monkeypatch, authenticated_client):
    monkeypatch.setattr(
        user_views.RetrieveUpdateUser, "permission_classes", [IsAdminUser]
    )

    response = authenticated_client.get(ME_URL)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_retrieve_user_not_found(anonymous_client):
    response = anonymous_client.get("/api/users/me/unknown/")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_user_partial(authenticated_client):
    response = authenticated_client.patch(
        ME_URL, {"first_name": "Updated"}, format="json"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["data"]["first_name"] == "Updated"


def test_update_user_full(authenticated_client):
    response = authenticated_client.patch(ME_URL, build_update_payload(), format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["data"]["location"] == "Abuja, NG"


def test_update_user_invalid_payload(authenticated_client):
    response = authenticated_client.patch(
        ME_URL, {"phone_number": "123"}, format="json"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_update_user_unauthorized(anonymous_client):
    response = anonymous_client.patch(
        ME_URL, {"first_name": "Updated"}, format="json"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_update_user_forbidden(monkeypatch, authenticated_client):
    monkeypatch.setattr(
        user_views.RetrieveUpdateUser, "permission_classes", [IsAdminUser]
    )

    response = authenticated_client.patch(
        ME_URL, {"first_name": "Updated"}, format="json"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_become_creator_success(authenticated_client, user):
    response = authenticated_client.post(BECOME_CREATOR_URL, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["data"]["is_creator"] is True
    user.refresh_from_db()
    assert user.is_creator is True


def test_become_creator_unauthorized(anonymous_client):
    response = anonymous_client.post(BECOME_CREATOR_URL, format="json")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_become_creator_forbidden(monkeypatch, authenticated_client):
    monkeypatch.setattr(user_views.BecomeCreator, "permission_classes", [IsAdminUser])

    response = authenticated_client.post(BECOME_CREATOR_URL, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_become_creator_invalid_payload():
    user = UserFactory(is_creator=True)
    client = APIClient()
    token = user.retrieve_auth_token()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token['access']}")

    response = client.post(BECOME_CREATOR_URL, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_become_creator_not_found(anonymous_client):
    response = anonymous_client.post("/api/users/me/become-creator/unknown/", format="json")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_logout_success(user):
    token = user.retrieve_auth_token()
    UserSessionFactory(user=user, refresh=token["refresh"], access=token["access"])

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token['access']}")

    response = client.post(LOGOUT_URL, {"refresh": token["refresh"]}, format="json")

    assert response.status_code == status.HTTP_205_RESET_CONTENT


def test_logout_unauthorized(anonymous_client):
    response = anonymous_client.post(LOGOUT_URL, {"refresh": "invalid"}, format="json")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_logout_forbidden(monkeypatch, authenticated_client):
    monkeypatch.setattr(user_views.Logout, "permission_classes", [IsAdminUser])

    response = authenticated_client.post(LOGOUT_URL, {"refresh": "invalid"}, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_logout_invalid_payload(authenticated_client):
    response = authenticated_client.post(LOGOUT_URL, {}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_logout_not_found(anonymous_client):
    response = anonymous_client.post("/api/auth/logout/unknown/", format="json")

    assert response.status_code == status.HTTP_404_NOT_FOUND
