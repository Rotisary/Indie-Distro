from django.urls import reverse

import pytest
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.test import APIClient

from core.utils.helpers.payment.handlers import PaymentHandlers
from core.webhook import views as webhook_views

pytestmark = pytest.mark.django_db

WEBHOOK_URL = reverse("flutterwave-webhook")


def build_headers(settings, secret=None):
    if secret is None:
        secret = getattr(settings, "FLW_WEBHOOK_SECRET", None)
    if not secret:
        return {}
    return {"HTTP_VERIF_HASH": secret}


def build_payload(event, **data):
    return {"event": event, "data": data}


def test_flutterwave_webhook_charge_completed_success(
    anonymous_client, monkeypatch, settings
):
    settings.FLW_WEBHOOK_SECRET = "test-secret"

    seen = {}

    def fake_handle(data):
        seen["data"] = data
        return {"status": "ok"}

    monkeypatch.setattr(
        PaymentHandlers, "handle_bank_charge", staticmethod(fake_handle)
    )

    response = anonymous_client.post(
        WEBHOOK_URL,
        build_payload("charge.completed", reference="tx-123", amount=500),
        format="json",
        **build_headers(settings),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "ok"
    assert seen["data"]["reference"] == "tx-123"


@pytest.mark.parametrize(
    "event", ["transfer.completed", "transfer.disburse", "transfer.failed"]
)
def test_flutterwave_webhook_transfer_event_success(
    anonymous_client, monkeypatch, settings, event
):
    settings.FLW_WEBHOOK_SECRET = "test-secret"

    seen = {}

    def fake_handle(data):
        seen["data"] = data
        return {"status": "queued"}

    monkeypatch.setattr(
        PaymentHandlers, "handle_transfer_event", staticmethod(fake_handle)
    )

    response = anonymous_client.post(
        WEBHOOK_URL,
        build_payload(event, reference="tx-999"),
        format="json",
        **build_headers(settings),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "queued"
    assert seen["data"]["reference"] == "tx-999"


def test_flutterwave_webhook_ignored_event_success(anonymous_client, settings):
    settings.FLW_WEBHOOK_SECRET = "test-secret"

    response = anonymous_client.post(
        WEBHOOK_URL,
        build_payload("unknown.event", payload="noop"),
        format="json",
        **build_headers(settings),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "ignored"


def test_flutterwave_webhook_unauthorized_invalid_hash(anonymous_client, settings):
    settings.FLW_WEBHOOK_SECRET = "test-secret"

    response = anonymous_client.post(
        WEBHOOK_URL,
        build_payload("charge.completed", reference="tx-unauth"),
        format="json",
        HTTP_VERIF_HASH="wrong-secret",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_flutterwave_webhook_missing_verification_hash(anonymous_client, settings):
    settings.FLW_WEBHOOK_SECRET = "test-secret"

    response = anonymous_client.post(
        WEBHOOK_URL,
        build_payload("charge.completed", reference="tx-missing"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_flutterwave_webhook_forbidden_when_admin_required(
    authenticated_client, monkeypatch, settings
):
    settings.FLW_WEBHOOK_SECRET = "test-secret"

    monkeypatch.setattr(
        webhook_views.FlutterwaveWebhook, "permission_classes", [IsAdminUser]
    )

    response = authenticated_client.post(
        WEBHOOK_URL,
        build_payload("charge.completed", reference="tx-forbidden"),
        format="json",
        **build_headers(settings),
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_flutterwave_webhook_invalid_payload_returns_bad_request(settings):
    settings.FLW_WEBHOOK_SECRET = None

    client = APIClient()
    response = client.post(
        WEBHOOK_URL, "{invalid-json", content_type="application/json"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_flutterwave_webhook_not_found(anonymous_client):
    response = anonymous_client.post(
        "/api/webhook/flutterwave/unknown/",
        build_payload("charge.completed", reference="tx-missing"),
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
