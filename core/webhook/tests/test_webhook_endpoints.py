from django.urls import reverse

import pytest
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.test import APIClient

from core.utils import enums
from core.utils.helpers.payment.handlers import PaymentHandlers
from core.webhook import views as webhook_views
from core.webhook.models import ProviderWebhookEvent

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
        build_payload(
            "charge.completed",
            reference="tx-123",
            amount=500,
            status="successful",
        ),
        format="json",
        **build_headers(settings),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "ok"
    assert seen["data"]["reference"] == "tx-123"

    persisted = ProviderWebhookEvent.objects.get(
        tx_ref="tx-123", event="charge.completed"
    )
    assert persisted.provider == enums.WebhookProvider.FLUTTERWAVE.value
    assert persisted.processing_state == enums.WebhookProcessingState.ACKNOWLEDGED.value
    assert persisted.payload["data"]["reference"] == "tx-123"
    assert persisted.handler_response == {"status": "ok"}


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
        build_payload(event, reference="tx-999", status="successful"),
        format="json",
        **build_headers(settings),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "queued"
    assert seen["data"]["reference"] == "tx-999"

    persisted = ProviderWebhookEvent.objects.get(tx_ref="tx-999", event=event)
    assert persisted.processing_state == enums.WebhookProcessingState.ACKNOWLEDGED.value
    assert persisted.provider_status == "successful"


def test_flutterwave_webhook_is_idempotent_for_duplicate_payload(
    anonymous_client, monkeypatch, settings
):
    settings.FLW_WEBHOOK_SECRET = "test-secret"

    seen = {"count": 0}

    def fake_handle(data):
        seen["count"] += 1
        return {"status": "queued"}

    monkeypatch.setattr(
        PaymentHandlers, "handle_transfer_event", staticmethod(fake_handle)
    )

    payload = build_payload(
        "transfer.completed",
        id=77,
        reference="tx-dup-1",
        status="successful",
        amount=500,
    )

    first = anonymous_client.post(
        WEBHOOK_URL,
        payload,
        format="json",
        **build_headers(settings),
    )
    second = anonymous_client.post(
        WEBHOOK_URL,
        payload,
        format="json",
        **build_headers(settings),
    )

    assert first.status_code == status.HTTP_200_OK
    assert second.status_code == status.HTTP_200_OK
    assert seen["count"] == 1
    assert ProviderWebhookEvent.objects.filter(tx_ref="tx-dup-1").count() == 1


def test_flutterwave_webhook_ignored_event_success(anonymous_client, settings):
    settings.FLW_WEBHOOK_SECRET = "test-secret"

    response = anonymous_client.post(
        WEBHOOK_URL,
        build_payload("unknown.event", payload="noop", status="ignored"),
        format="json",
        **build_headers(settings),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "ignored"

    persisted = ProviderWebhookEvent.objects.get(event="unknown.event")
    assert persisted.processing_state == enums.WebhookProcessingState.IGNORED.value


def test_flutterwave_webhook_unauthorized_invalid_hash(anonymous_client, settings):
    settings.FLW_WEBHOOK_SECRET = "test-secret"

    response = anonymous_client.post(
        WEBHOOK_URL,
        build_payload("charge.completed", reference="tx-unauth", status="successful"),
        format="json",
        HTTP_VERIF_HASH="wrong-secret",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_flutterwave_webhook_missing_verification_hash(anonymous_client, settings):
    settings.FLW_WEBHOOK_SECRET = "test-secret"

    response = anonymous_client.post(
        WEBHOOK_URL,
        build_payload("charge.completed", reference="tx-missing", status="successful"),
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
        build_payload(
            "charge.completed", reference="tx-forbidden", status="successful"
        ),
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
