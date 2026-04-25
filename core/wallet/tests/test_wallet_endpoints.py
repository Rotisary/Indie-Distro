from decimal import Decimal

from django.urls import reverse

import pytest
from rest_framework import status

from core.wallet import views as wallet_views
from core.wallet.tests.factories.wallet_factories import WalletFactory
from core.utils.services.flutterwave import FlutterwaveService

pytestmark = pytest.mark.django_db

FUND_WITH_BANK_CHARGE_URL = reverse("fund-with-bank-charge ")
INITIATE_PAYOUT_URL = reverse("initiate-payout")


def fetch_virtual_account_url(account_reference):
    return reverse("fetch-virtual-account", args=[account_reference])


def set_wallet_pin_url(account_reference):
    return reverse("set-wallet-pin", args=[account_reference])


def change_wallet_pin_url(account_reference):
    return reverse("change-wallet-pin", args=[account_reference])


def build_fund_wallet_payload(**overrides):
    payload = {
        "amount": "100.00",
        "wallet_pin": "1234",
    }
    payload.update(overrides)
    return payload


def build_payout_payload(**overrides):
    payload = {
        "amount": "100.00",
        "wallet_pin": "1234",
        "bank": "044",
        "account_number": "0123456789",
        "name": "Test User",
    }
    payload.update(overrides)
    return payload


def build_set_pin_payload(pin="1234"):
    return {"pin": pin}


def build_change_pin_payload(old_pin="1234", new_pin="4321", **overrides):
    payload = {"old_pin": old_pin, "new_pin": new_pin}
    payload.update(overrides)
    return payload


def build_balance_response(balance, currency="NGN"):
    def fake_balance(self, account_reference, currency=currency):
        return {
            "status": "success",
            "balance": Decimal(str(balance)),
            "currency": currency,
        }

    return fake_balance


@pytest.fixture
def creator_wallet_with_earnings(creator_user):
    return WalletFactory(
        owner=creator_user,
        wallet_pin="1234",
        earnings_balance=Decimal("250.00"),
        total_balance=Decimal("250.00"),
    )


# Fetch virtual account


def test_fetch_virtual_account_success(creator_client, creator_wallet, monkeypatch):
    calls = {"count": 0}

    def fake_delay(wallet_id):
        calls["count"] += 1
        assert wallet_id == creator_wallet.pk

    monkeypatch.setattr(
        wallet_views.fetch_virtual_account_for_wallet, "delay", fake_delay
    )

    response = creator_client.get(
        fetch_virtual_account_url(creator_wallet.account_reference)
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.data["status"] == "in progress"
    assert calls["count"] == 1


def test_fetch_virtual_account_unauthorized(anonymous_client, creator_wallet):
    response = anonymous_client.get(
        fetch_virtual_account_url(creator_wallet.account_reference)
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_fetch_virtual_account_forbidden(other_creator_client, creator_wallet):
    response = other_creator_client.get(
        fetch_virtual_account_url(creator_wallet.account_reference)
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_fetch_virtual_account_not_found(creator_client):
    response = creator_client.get(fetch_virtual_account_url("missing-wallet"))

    assert response.status_code == status.HTTP_404_NOT_FOUND


# Fund wallet with bank charge


def test_fund_with_bank_charge_success(monkeypatch, creator_client, creator_wallet):
    def fake_charge_bank(self):
        return self.PaymentResponse(status="initiated", data={"ok": True})

    monkeypatch.setattr(
        wallet_views.payment.PaymentHelper, "charge_bank", fake_charge_bank
    )

    response = creator_client.post(
        FUND_WITH_BANK_CHARGE_URL, build_fund_wallet_payload(), format="json"
    )

    assert response.status_code == status.HTTP_202_ACCEPTED


def test_fund_with_bank_charge_unauthorized(anonymous_client):
    response = anonymous_client.post(
        FUND_WITH_BANK_CHARGE_URL, build_fund_wallet_payload(), format="json"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_fund_with_bank_charge_forbidden(authenticated_client):
    response = authenticated_client.post(
        FUND_WITH_BANK_CHARGE_URL, build_fund_wallet_payload(), format="json"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_fund_with_bank_charge_invalid_payload(creator_client, creator_wallet):
    response = creator_client.post(
        FUND_WITH_BANK_CHARGE_URL,
        build_fund_wallet_payload(wallet_pin="12"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_fund_with_bank_charge_missing_required_fields(creator_client, creator_wallet):
    response = creator_client.post(FUND_WITH_BANK_CHARGE_URL, {}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_fund_with_bank_charge_not_found(anonymous_client):
    response = anonymous_client.post(
        "/api/wallet/fund-with-bank-charge/unknown/",
        build_fund_wallet_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# Initiate payout


def test_initiate_payout_success(
    monkeypatch, creator_client, creator_wallet_with_earnings
):
    def fake_transfer(self, **kwargs):
        return self.PaymentResponse(status="initiated", data={"ok": True})

    monkeypatch.setattr(
        FlutterwaveService,
        "check_payout_subaccount_balance",
        build_balance_response("250.00"),
    )
    monkeypatch.setattr(wallet_views.payment.PaymentHelper, "transfer", fake_transfer)

    response = creator_client.post(
        INITIATE_PAYOUT_URL, build_payout_payload(), format="json"
    )

    assert response.status_code == status.HTTP_202_ACCEPTED


def test_initiate_payout_flutterwave_balance_mismatch(
    monkeypatch, creator_client, creator_wallet_with_earnings
):
    monkeypatch.setattr(
        FlutterwaveService,
        "check_payout_subaccount_balance",
        build_balance_response("200.00"),
    )

    response = creator_client.post(
        INITIATE_PAYOUT_URL, build_payout_payload(), format="json"
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_initiate_payout_flutterwave_balance_insufficient(
    monkeypatch, creator_client, creator_wallet_with_earnings
):
    creator_wallet_with_earnings.earnings_balance = Decimal("50.00")
    creator_wallet_with_earnings.total_balance = Decimal("50.00")
    creator_wallet_with_earnings.save(
        update_fields=["earnings_balance", "total_balance"]
    )

    monkeypatch.setattr(
        FlutterwaveService,
        "check_payout_subaccount_balance",
        build_balance_response("50.00"),
    )

    response = creator_client.post(
        INITIATE_PAYOUT_URL, build_payout_payload(), format="json"
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_initiate_payout_unauthorized(anonymous_client):
    response = anonymous_client.post(
        INITIATE_PAYOUT_URL, build_payout_payload(), format="json"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_initiate_payout_forbidden(authenticated_client):
    response = authenticated_client.post(
        INITIATE_PAYOUT_URL, build_payout_payload(), format="json"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_initiate_payout_invalid_payload(creator_client, creator_wallet_with_earnings):
    response = creator_client.post(
        INITIATE_PAYOUT_URL,
        build_payout_payload(wallet_pin="12"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_initiate_payout_missing_required_fields(
    creator_client, creator_wallet_with_earnings
):
    response = creator_client.post(INITIATE_PAYOUT_URL, {}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_initiate_payout_not_found(anonymous_client):
    response = anonymous_client.post(
        "/api/wallet/payouts/initiate/unknown/",
        build_payout_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# Set wallet PIN


def test_set_wallet_pin_success(creator_client, creator_wallet):
    response = creator_client.post(
        set_wallet_pin_url(creator_wallet.account_reference),
        build_set_pin_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "success"


def test_set_wallet_pin_unauthorized(anonymous_client, creator_wallet):
    response = anonymous_client.post(
        set_wallet_pin_url(creator_wallet.account_reference),
        build_set_pin_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_set_wallet_pin_forbidden(other_creator_client, creator_wallet):
    response = other_creator_client.post(
        set_wallet_pin_url(creator_wallet.account_reference),
        build_set_pin_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_set_wallet_pin_invalid_payload(creator_client, creator_wallet):
    response = creator_client.post(
        set_wallet_pin_url(creator_wallet.account_reference),
        build_set_pin_payload(pin="12"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_set_wallet_pin_missing_required_fields(creator_client, creator_wallet):
    response = creator_client.post(
        set_wallet_pin_url(creator_wallet.account_reference),
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_set_wallet_pin_not_found(creator_client):
    response = creator_client.post(
        set_wallet_pin_url("missing-wallet"),
        build_set_pin_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# Change wallet PIN


def test_change_wallet_pin_success(creator_client, creator_wallet):
    response = creator_client.post(
        change_wallet_pin_url(creator_wallet.account_reference),
        build_change_pin_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "success"


def test_change_wallet_pin_unauthorized(anonymous_client, creator_wallet):
    response = anonymous_client.post(
        change_wallet_pin_url(creator_wallet.account_reference),
        build_change_pin_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_change_wallet_pin_forbidden(other_creator_client, creator_wallet):
    response = other_creator_client.post(
        change_wallet_pin_url(creator_wallet.account_reference),
        build_change_pin_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_change_wallet_pin_invalid_payload(creator_client, creator_wallet):
    response = creator_client.post(
        change_wallet_pin_url(creator_wallet.account_reference),
        build_change_pin_payload(new_pin="12"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_change_wallet_pin_missing_required_fields(creator_client, creator_wallet):
    response = creator_client.post(
        change_wallet_pin_url(creator_wallet.account_reference),
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_change_wallet_pin_not_found(creator_client):
    response = creator_client.post(
        change_wallet_pin_url("missing-wallet"),
        build_change_pin_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
