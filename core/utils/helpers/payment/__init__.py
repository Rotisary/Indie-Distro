from django.db import transaction as db_transaction
from django.utils import timezone

from .base import *


class PostLedgerData:

    @staticmethod
    def as_pending(
        ledger_data: list[dict],
        tx_purpose: str,
        type: str,
        currency: str = None,
        description: str = None,
        parent_transaction: Transaction = None,
    ):
        with db_transaction.atomic():
            transaction = PaymentLedgerCreatorHelpers.create_ledger_transaction(
                tx_purpose=tx_purpose,
                description=description,
                type=type,
                parent_transaction=parent_transaction,
            )
            journal = PaymentLedgerCreatorHelpers.add_transaction_to_journal(
                transaction
            )
            for data in ledger_data:
                ledger_account = (
                    PaymentLedgerCreatorHelpers.get_or_create_ledger_account(
                        user=data["user"], type=data["account_type"]
                    )
                )
                ledger_entry = PaymentLedgerCreatorHelpers.create_ledger_entry(
                    journal=journal,
                    account=ledger_account,
                    entry_type=data["entry_type"],
                    amount=data["amount"],
                )
            return transaction

    @staticmethod
    def as_successful(tx: Transaction, data: dict, type: str):
        with db_transaction.atomic():
            entries = JournalEntry.objects.filter(
                journal__transaction=tx,
                status=enums.EntryStatus.PENDING.value,
            )
            updated = entries.update(
                status=enums.EntryStatus.COMPLETED.value, completed_at=timezone.now()
            )

            tx.status = enums.TransactionStatus.SUCCESSFUL.value
            tx.finalisation_state = (
                enums.TransactionFinalisationState.SUCCESS_FINALISED.value
            )
            tx.successful_at = timezone.now()
            metadata = tx.metadata or {}
            metadata[f"flw_{type}_webhook"] = data
            tx.save(
                update_fields=[
                    "status",
                    "finalisation_state",
                    "successful_at",
                    "metadata",
                ]
            )

            logger.info(f"Completed {updated} journal entries for tx {tx.reference}")

    @staticmethod
    def as_failed(tx: Transaction, data: dict, type: str):
        entries = JournalEntry.objects.filter(
            journal__transaction=tx,
            status=enums.EntryStatus.PENDING.value,
        )
        updated = entries.update(status=enums.EntryStatus.FAILED.value)

        tx.status = enums.TransactionStatus.FAILED.value
        tx.finalisation_state = enums.TransactionFinalisationState.FAILED_FINALISED.value
        tx.failed_at = timezone.now()
        metadata = tx.metadata or {}
        metadata[f"flw_{type}_webhook"] = data
        tx.save(
            update_fields=["status", "finalisation_state", "failed_at", "metadata"]
        )

        logger.info(f"Failed {updated} journal entries for tx {tx.reference}")
