from django.urls import reverse

import pytest
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.test import APIClient

from core.feed.tests.factories.purchase_factories import PurchaseFactory
from core.playback import views as playback_views

pytestmark = pytest.mark.django_db

RETRIEVE_FILM_PLAYBACK_URL = reverse("retrieve-film-playback-url")
REFRESH_FILM_PLAYBACK_COOKIE_URL = reverse("refresh-film-playback-cookie")
RETRIEVE_SHORT_PLAYBACK_URL = reverse("retrieve-short-playback-url")
REFRESH_SHORT_PLAYBACK_COOKIE_URL = reverse("refresh-short-playback-cookie")


def build_film_payload(film_id):
    return {"film_id": film_id}


def build_short_payload(short_id):
    return {"short_id": short_id}


# Retrieve film playback URL


def test_retrieve_film_playback_url_success(
    buyer_client,
    active_purchase,
    stream_playback_settings,
):
    response = buyer_client.post(
        RETRIEVE_FILM_PLAYBACK_URL,
        build_film_payload(active_purchase.film.id),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert "url" in response.data
    assert "expires_at" in response.data
    assert response.cookies.get(stream_playback_settings.STREAM_COOKIE_NAME) is not None


def test_retrieve_film_playback_url_unauthorized(anonymous_client):
    response = anonymous_client.post(
        RETRIEVE_FILM_PLAYBACK_URL,
        build_film_payload(1),
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_retrieve_film_playback_url_forbidden(
    authenticated_client,
    released_film_with_playback,
):
    response = authenticated_client.post(
        RETRIEVE_FILM_PLAYBACK_URL,
        build_film_payload(released_film_with_playback.id),
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_retrieve_film_playback_url_invalid_payload(authenticated_client):
    response = authenticated_client.post(RETRIEVE_FILM_PLAYBACK_URL, {}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_retrieve_film_playback_url_not_found(
    buyer_client,
    buyer_user,
    released_film,
):
    purchase = PurchaseFactory(owner=buyer_user, film=released_film)

    response = buyer_client.post(
        RETRIEVE_FILM_PLAYBACK_URL,
        build_film_payload(purchase.film.id),
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# Refresh film playback cookie


def test_refresh_film_playback_cookie_success(
    buyer_client,
    active_purchase,
    stream_playback_settings,
):
    response = buyer_client.post(
        REFRESH_FILM_PLAYBACK_COOKIE_URL,
        build_film_payload(active_purchase.film.id),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert "expires_at" in response.data
    assert response.cookies.get(stream_playback_settings.STREAM_COOKIE_NAME) is not None


def test_refresh_film_playback_cookie_unauthorized(anonymous_client):
    response = anonymous_client.post(
        REFRESH_FILM_PLAYBACK_COOKIE_URL,
        build_film_payload(1),
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_refresh_film_playback_cookie_forbidden(
    authenticated_client,
    released_film_with_playback,
):
    response = authenticated_client.post(
        REFRESH_FILM_PLAYBACK_COOKIE_URL,
        build_film_payload(released_film_with_playback.id),
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_refresh_film_playback_cookie_invalid_payload(authenticated_client):
    response = authenticated_client.post(
        REFRESH_FILM_PLAYBACK_COOKIE_URL,
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_refresh_film_playback_cookie_not_found(
    buyer_client,
    buyer_user,
    released_film,
):
    purchase = PurchaseFactory(owner=buyer_user, film=released_film)

    response = buyer_client.post(
        REFRESH_FILM_PLAYBACK_COOKIE_URL,
        build_film_payload(purchase.film.id),
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# Retrieve short playback URL


def test_retrieve_short_playback_url_success(
    anonymous_client,
    released_short_with_playback,
    stream_playback_settings,
):
    response = anonymous_client.post(
        RETRIEVE_SHORT_PLAYBACK_URL,
        build_short_payload(released_short_with_playback.id),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert "url" in response.data
    assert "expires_at" in response.data
    assert response.cookies.get(stream_playback_settings.STREAM_COOKIE_NAME) is not None


def test_retrieve_short_playback_url_unauthorized(monkeypatch, anonymous_client):
    monkeypatch.setattr(
        playback_views.RetrieveShortPlaybackURL,
        "permission_classes",
        [IsAuthenticated],
    )

    response = anonymous_client.post(
        RETRIEVE_SHORT_PLAYBACK_URL,
        build_short_payload(1),
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_retrieve_short_playback_url_forbidden(monkeypatch, user):
    monkeypatch.setattr(
        playback_views.RetrieveShortPlaybackURL,
        "permission_classes",
        [IsAdminUser],
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        RETRIEVE_SHORT_PLAYBACK_URL,
        build_short_payload(1),
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_retrieve_short_playback_url_invalid_payload(anonymous_client):
    response = anonymous_client.post(RETRIEVE_SHORT_PLAYBACK_URL, {}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_retrieve_short_playback_url_not_found(anonymous_client):
    response = anonymous_client.post(
        RETRIEVE_SHORT_PLAYBACK_URL,
        build_short_payload(999999),
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# Refresh short playback cookie


def test_refresh_short_playback_cookie_success(
    anonymous_client,
    released_short_with_playback,
    stream_playback_settings,
):
    response = anonymous_client.post(
        REFRESH_SHORT_PLAYBACK_COOKIE_URL,
        build_short_payload(released_short_with_playback.id),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert "expires_at" in response.data
    assert response.cookies.get(stream_playback_settings.STREAM_COOKIE_NAME) is not None


def test_refresh_short_playback_cookie_unauthorized(monkeypatch, anonymous_client):
    monkeypatch.setattr(
        playback_views.RefreshShortPlaybackCookie,
        "permission_classes",
        [IsAuthenticated],
    )

    response = anonymous_client.post(
        REFRESH_SHORT_PLAYBACK_COOKIE_URL,
        build_short_payload(1),
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_refresh_short_playback_cookie_forbidden(monkeypatch, user):
    monkeypatch.setattr(
        playback_views.RefreshShortPlaybackCookie,
        "permission_classes",
        [IsAdminUser],
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        REFRESH_SHORT_PLAYBACK_COOKIE_URL,
        build_short_payload(1),
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_refresh_short_playback_cookie_invalid_payload(anonymous_client):
    response = anonymous_client.post(
        REFRESH_SHORT_PLAYBACK_COOKIE_URL,
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_refresh_short_playback_cookie_not_found(anonymous_client):
    response = anonymous_client.post(
        REFRESH_SHORT_PLAYBACK_COOKIE_URL,
        build_short_payload(999999),
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
