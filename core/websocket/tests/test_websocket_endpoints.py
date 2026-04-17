from django.urls import reverse

import pytest
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.test import APIClient

from core.websocket import views as websocket_views
from core.websocket.tests.factories.event_log_factories import EventLogFactory

pytestmark = pytest.mark.django_db

EVENT_REPLAY_URL = reverse("websocket-event-replay")


def test_event_replay_success_returns_events(authenticated_client, user):
    EventLogFactory(
        user=user,
        type="wallet.updated",
        payload={"event": "wallet.updated", "status": "ok"},
    )
    EventLogFactory(
        user=user,
        type="file.processing",
        payload={"event": "file.processing", "status": "ok"},
    )

    response = authenticated_client.get(EVENT_REPLAY_URL)

    assert response.status_code == status.HTTP_200_OK
    assert {item["type"] for item in response.data} == {
        "wallet.updated",
        "file.processing",
    }
    for item in response.data:
        assert "data" in item
        assert "timestamp" in item
        assert isinstance(item["data"], dict)


def test_event_replay_filters_to_authenticated_user(
    authenticated_client, user, other_creator_user
):
    EventLogFactory(user=user, type="wallet.updated")
    EventLogFactory(user=other_creator_user, type="payment.failed")

    response = authenticated_client.get(EVENT_REPLAY_URL)

    assert response.status_code == status.HTTP_200_OK
    assert {item["type"] for item in response.data} == {"wallet.updated"}


def test_event_replay_limit_pagination(authenticated_client, user):
    EventLogFactory.create_batch(3, user=user)

    response = authenticated_client.get(EVENT_REPLAY_URL, {"limit": 2})

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 2


def test_event_replay_empty_list(authenticated_client):
    response = authenticated_client.get(EVENT_REPLAY_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data == []


def test_event_replay_unauthorized(anonymous_client):
    response = anonymous_client.get(EVENT_REPLAY_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_event_replay_forbidden_when_admin_required(authenticated_client, monkeypatch):
    monkeypatch.setattr(
        websocket_views.EventReplayView,
        "permission_classes",
        [IsAdminUser],
    )

    response = authenticated_client.get(EVENT_REPLAY_URL)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_event_replay_invalid_limit_returns_bad_request(user):
    client = APIClient()
    token = user.retrieve_auth_token()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token['access']}")

    response = client.get(EVENT_REPLAY_URL, {"limit": "invalid"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_event_replay_not_found(anonymous_client):
    response = anonymous_client.get("/api/websocket/events/last/missing/")

    assert response.status_code == status.HTTP_404_NOT_FOUND
