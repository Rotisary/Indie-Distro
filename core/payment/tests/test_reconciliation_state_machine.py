from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from core.payment.models import JournalEntry, LedgerAccount, LedgerJournal, Transaction
from core.payment.tasks import reconcile_flutterwave_finalization_failures
from core.utils import enums
from core.utils.helpers.payment import PostLedgerData
from core.utils.helpers.payment.handlers import PaymentHandlers
from core.wallet.tests.factories.wallet_factories import WalletFactory
from core.webhook.models import ProviderWebhookEvent

pytestmark = pytest.mark.django_db


def build_payout_transaction(user, suffix: str, finalisation_state: str, metadata=None):
    WalletFactory(owner=user)
    tx = Transaction.objects.create(
        reference=f"txr{suffix}",
        status=enums.TransactionStatus.INITIATED.value,
        finalisation_state=finalisation_state,
        currency=enums.SupportedCurrency.NGN.value,
        purpose=enums.TransactionPurpose.PAYOUT.value,
        metadata=metadata or {},
    )
    account, _ = LedgerAccount.objects.get_or_create(
        owner=user,
        type=enums.LedgerAccountType.USER_WALLET.value,
        currency=enums.SupportedCurrency.NGN.value,
    )
    journal = LedgerJournal.objects.create(transaction=tx)
    JournalEntry.objects.create(
        account=account,
        journal=journal,
        line_no=1,
        type=enums.EntryType.DEBIT.value,
        status=enums.EntryStatus.PENDING.value,
        amount=Decimal("100.00"),
    )
    return tx


def build_webhook_event(tx: Transaction, status_value: str, suffix: str):
    return ProviderWebhookEvent.objects.create(
        provider=enums.WebhookProvider.FLUTTERWAVE.value,
        event="transfer.completed",
        idempotency_key=f"flutterwave-transfer-{suffix}",
        tx_ref=tx.reference,
        provider_event_id=suffix,
        provider_status=status_value,
        payload={
            "event": "transfer.completed",
            "data": {
                "id": suffix,
                "reference": tx.reference,
                "status": status_value,
                "amount": "100.00",
            },
        },
        processing_state=enums.WebhookProcessingState.ACKNOWLEDGED.value,
    )


def test_reconcile_uses_persisted_webhook_outcome_and_finalises_as_failed(
    monkeypatch, user
):
    monkeypatch.setattr(
        PaymentHandlers, "_emit_payment_event", staticmethod(lambda *args, **kwargs: None)
    )

    tx = build_payout_transaction(
        user,
        suffix="100001",
        finalisation_state=enums.TransactionFinalisationState.SUCCESS_NOT_FINALISED.value,
    )
    build_webhook_event(tx, "successful", "evt-1")

    result = PaymentHandlers.reconcile_transaction_finalization(tx.reference)

    tx.refresh_from_db()
    entry = tx.journal.entries.get(line_no=1)

    assert result["status"] == "failed"
    assert tx.status == enums.TransactionStatus.FAILED.value
    assert tx.finalisation_state == enums.TransactionFinalisationState.FAILED_FINALISED.value
    assert tx.metadata["provider_outcome"]["status"] == "successful"
    assert entry.status == enums.EntryStatus.FAILED.value


def test_reconcile_moves_to_failed_not_finalised_when_failed_finalisation_fails(
    monkeypatch, user
):
    monkeypatch.setattr(
        PaymentHandlers, "_emit_payment_event", staticmethod(lambda *args, **kwargs: None)
    )

    tx = build_payout_transaction(
        user,
        suffix="100002",
        finalisation_state=enums.TransactionFinalisationState.SUCCESS_NOT_FINALISED.value,
    )
    build_webhook_event(tx, "successful", "evt-2")

    def raise_failed_post(*args, **kwargs):
        raise RuntimeError("ledger write failed")

    monkeypatch.setattr(PostLedgerData, "as_failed", staticmethod(raise_failed_post))

    result = PaymentHandlers.reconcile_transaction_finalization(tx.reference)

    tx.refresh_from_db()

    assert result["status"] == "failed"
    assert result["detail"] == "reconciliation required"
    assert tx.finalisation_state == enums.TransactionFinalisationState.FAILED_NOT_FINALISED.value
    assert tx.metadata["provider_outcome"]["status"] == "successful"


def test_reconcile_task_filters_by_finalisation_state_and_provider_outcome(
    monkeypatch, user, other_creator_user
):
    tx_not_finalised = build_payout_transaction(
        user,
        suffix="100003",
        finalisation_state=enums.TransactionFinalisationState.FAILED_NOT_FINALISED.value,
    )
    tx_finalised = build_payout_transaction(
        other_creator_user,
        suffix="100004",
        finalisation_state=enums.TransactionFinalisationState.SUCCESS_FINALISED.value,
    )
    tx_pending_with_outcome = build_payout_transaction(
        other_creator_user,
        suffix="100005",
        finalisation_state=enums.TransactionFinalisationState.PENDING.value,
        metadata={"provider_outcome": {"status": "failed", "payload": {"x": 1}}},
    )

    threshold_time = timezone.now() - timedelta(minutes=5)
    Transaction.objects.filter(
        id__in=[tx_not_finalised.id, tx_finalised.id, tx_pending_with_outcome.id]
    ).update(date_added=threshold_time)

    seen = []

    def fake_reconcile(tx_ref):
        seen.append(tx_ref)
        return {"status": "failed", "tx_ref": tx_ref}

    monkeypatch.setattr(
        PaymentHandlers, "reconcile_transaction_finalization", staticmethod(fake_reconcile)
    )

    result = reconcile_flutterwave_finalization_failures.run(batch_size=10)

    assert result["processed"] == 2
    assert tx_not_finalised.reference in seen
    assert tx_pending_with_outcome.reference in seen
    assert tx_finalised.reference not in seen
