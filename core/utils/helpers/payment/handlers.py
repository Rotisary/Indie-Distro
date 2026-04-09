from loguru import logger
from decimal import Decimal
from datetime import timedelta

from django.db import transaction as db_transaction
from django.utils import timezone

from core.payment.models import Transaction, JournalEntry
from core.utils import enums
from core.utils.helpers.payment import PostLedgerData
from core.websocket.utils import emit_user_event
from .base import PaymentHelper
from core.feed.models import Purchase


class PaymentHandlers:

    @staticmethod
    def _resolve_event_user(tx: Transaction, purchase: Purchase = None):
        if tx.purpose == enums.TransactionPurpose.PURCHASE.value:
            return purchase.owner if purchase else None

        if tx.purpose == enums.TransactionPurpose.PAYOUT.value:
            debit_entry = (
                JournalEntry.objects.filter(
                    journal__transaction=tx,
                    type=enums.EntryType.DEBIT.value,
                    account__type=enums.LedgerAccountType.USER_WALLET.value,
                )
                .select_related("account__owner")
                .first()
            )
            return debit_entry.account.owner if debit_entry else None

        if tx.purpose == enums.TransactionPurpose.FUNDING.value:
            credit_entry = (
                JournalEntry.objects.filter(
                    journal__transaction=tx,
                    type=enums.EntryType.CREDIT.value,
                    account__type=enums.LedgerAccountType.USER_WALLET.value,
                )
                .select_related("account__owner")
                .first()
            )
            if credit_entry:
                return credit_entry.account.owner

        return None

    @staticmethod
    def _emit_payment_event(tx: Transaction, success: bool, amount=None) -> None:
        event_type_map = {
            enums.TransactionPurpose.PURCHASE.value: (
                enums.PaymentEventType.PURCHASE_SUCCEEDED.value,
                enums.PaymentEventType.PURCHASE_FAILED.value,
            ),
            enums.TransactionPurpose.FUNDING.value: (
                enums.PaymentEventType.FUNDING_SUCCEEDED.value,
                enums.PaymentEventType.FUNDING_FAILED.value,
            ),
            enums.TransactionPurpose.PAYOUT.value: (
                enums.PaymentEventType.PAYOUT_SUCCEEDED.value,
                enums.PaymentEventType.PAYOUT_FAILED.value,
            ),
        }
        mapped = event_type_map.get(tx.purpose)
        if not mapped:
            return

        purchase = None
        purchase_id = None
        if tx.purpose == enums.TransactionPurpose.PURCHASE.value:
            purchase = (
                Purchase.objects.select_related("owner")
                .filter(
                    transaction=(
                        tx if not tx.parent_transaction else tx.parent_transaction
                    )
                )
                .first()
            )
            purchase_id = str(purchase.id) if purchase else None

        user = PaymentHandlers._resolve_event_user(tx, purchase=purchase)
        if not user:
            logger.error(
                "payment event skipped: no user for tx %s",
                tx.reference,
            )
            return

        payload = {
            "tx_ref": tx.reference,
            "purpose": tx.purpose,
            "status": "success" if success else "failed",
            "amount": amount,
            "user_id": user.id,
        }
        if purchase_id:
            payload["purchase_id"] = purchase_id

        event_type = mapped[0] if success else mapped[1]
        emit_user_event(user, event_type, payload, entity="payment")

    @staticmethod
    def _mark_purchase_completed(tx: Transaction):
        """
        Marks a Purchase linked to this Transaction as completed/active.
        Also sets rental expiry_time when applicable.
        """

        purchase = (
            Purchase.objects.select_related("film").filter(transaction=tx).first()
        )
        if not purchase:
            return

        updates = {
            "payment_status": enums.PurchasePaymentStatus.COMPLETED.value,
            "status": enums.PurchaseStatusType.ACTIVE.value,
        }

        film = purchase.film
        if (
            film
            and film.sale_type == enums.FilmSaleType.RENTAL.value
            and film.rental_duration
        ):
            updates["expiry_time"] = timezone.now() + timedelta(
                hours=int(film.rental_duration)
            )

        for k, v in updates.items():
            setattr(purchase, k, v)
        purchase.save(update_fields=[*updates.keys(), "date_last_modified"])

    def _mark_purchase_failed(tx: Transaction):
        """
        Marks a Purchase linked to this Transaction as failed.
        """

        purchase = (
            Purchase.objects.select_related("film").filter(transaction=tx).first()
        )
        if not purchase:
            return

        purchase.payment_status = enums.PurchasePaymentStatus.FAILED.value
        purchase.save(update_fields=["payment_status", "date_last_modified"])

    @staticmethod
    def _finalise_failed_charge(tx: Transaction, data: dict, flw_status: str) -> dict:
        PostLedgerData.as_failed(tx, data, "charge")
        PaymentHandlers._mark_purchase_failed(tx)
        PaymentHandlers._emit_payment_event(tx, success=False)
        logger.warning(f"charge.completed: tx {tx.reference} failed ({flw_status})")

        return {"status": "failed"}

    @staticmethod
    def _initiate_subaccount_transfer(charge_tx: Transaction, amount) -> None:
        """
        After a successful bank charge, transfer funds from the main
        Flutterwave account into the user's payout subaccount.
        """

        debit_entry = (
            JournalEntry.objects.filter(
                journal__transaction=charge_tx,
                type=enums.EntryType.DEBIT.value,
                account__type=(
                    enums.LedgerAccountType.FUNDING.value
                    if charge_tx.purpose == enums.TransactionPurpose.FUNDING.value
                    else enums.LedgerAccountType.EXTERNAL_PAYMENT.value
                ),
            )
            .select_related("account__owner")
            .first()
        )

        if not debit_entry:
            logger.error(f"No debit entry for charge tx {charge_tx.reference}")
            return {"status": "error", "detail": "missing debit entry"}

        user = None
        purchase = (
            Purchase.objects.select_related("film")
            .filter(transaction=charge_tx)
            .first()
        )
        if not purchase:
            user = debit_entry.account.owner

        user = purchase.film.owner
        entry_lines = [
            {
                "user": None,
                "account_type": enums.LedgerAccountType.PROVIDER_WALLET.value,
                "entry_type": enums.EntryType.DEBIT.value,
                "amount": amount,
            },
            {
                "user": user,
                "account_type": enums.LedgerAccountType.USER_WALLET.value,
                "entry_type": enums.EntryType.CREDIT.value,
                "amount": amount,
            },
        ]

        with db_transaction.atomic():
            transaction = PostLedgerData.as_pending(
                ledger_data=entry_lines,
                tx_purpose=charge_tx.purpose,
                description="bank charge completion via subaccount transfer",
                parent_transaction=charge_tx,
            )

            payment_helper = PaymentHelper(
                user=user,
                transaction=transaction,
                amount=amount,
                payment_type=enums.PaymentType.TRANSFER.value,
            )
            beneficiary = {
                "account_number": user.wallet.barter_id,
                "name": f"{user.first_name} {user.last_name}",
            }
            payment_helper.transfer(
                beneficiary=beneficiary,
                description="bank charge completion via subaccount transfer",
            )

    @staticmethod
    def _finalise_successful_transfer(tx: Transaction, data: dict, amount) -> dict:
        """
        Finalises successful transfers and move money from and to  the right balances
        """

        PostLedgerData.as_successful(tx, data, "transfer")

        credit_entry = (
            JournalEntry.objects.filter(
                journal__transaction=tx,
                type=enums.EntryType.CREDIT.value,
                account__type=enums.LedgerAccountType.USER_WALLET.value,
            )
            .select_related("account__owner")
            .first()
        )
        if not credit_entry:
            logger.error(
                f"No USER_WALLET credit entry for transfer tx {tx.reference} found"
            )
            return {"status": "error", "detail": "missing credit entry"}

        wallet = credit_entry.account.owner.wallet
        tx_purpose = tx.purpose

        if tx_purpose == enums.TransactionPurpose.FUNDING.value:
            wallet.pay_to_wallet(amount, is_funding=True)
        elif tx.purpose == enums.TransactionPurpose.PURCHASE.value:
            wallet.pay_to_wallet(amount)
            PaymentHandlers._mark_purchase_failed(
                tx.parent_transaction if tx.parent_transaction else tx
            )
        elif tx.purpose == enums.TransactionPurpose.PAYOUT.value:
            wallet.withdraw_funds(amount, is_earnings=True)

        PaymentHandlers._emit_payment_event(tx, success=True, amount=amount)

        logger.success(
            f"transfer.completed: tx {tx.reference} finalised ({tx_purpose})"
        )
        return {"status": "success"}

    @staticmethod
    def _finalise_failed_transfer(tx: Transaction, data: dict, flw_status: str) -> dict:

        PostLedgerData.as_failed(tx, data, "transfer")

        debit_entry = (
            JournalEntry.objects.filter(
                journal__transaction=tx, type=enums.EntryType.DEBIT.value
            )
            .select_related("account__owner")
            .first()
        )
        if not debit_entry:
            logger.error(f"No debit entry for transfer tx {tx.reference} found")
            return {"status": "error", "detail": "missing debit entry"}

        wallet = debit_entry.account.owner.wallet
        if tx.purpose == enums.TransactionPurpose.PAYOUT.value:
            wallet.pay_to_wallet(debit_entry.amount)
        elif tx.purpose == enums.TransactionPurpose.PURCHASE.value:
            wallet.pay_to_wallet(debit_entry.amount, is_funding=True)
            PaymentHandlers._mark_purchase_failed(
                tx.parent_transaction if tx.parent_transaction else tx
            )
        elif tx.purpose == enums.TransactionPurpose.FUNDING.value:
            wallet.pay_to_wallet(debit_entry.amount, is_funding=True)

        PaymentHandlers._emit_payment_event(
            tx, success=False, amount=debit_entry.amount
        )
        logger.warning(f"transfer.completed: tx {tx.reference} failed ({flw_status})")
        return {"status": "failed"}

    @staticmethod
    def handle_bank_charge(data: dict) -> dict:
        """
        Handle Flutterwave 'charge.completed' webhook.
        """
        tx_ref = data.get("tx_ref")
        flw_status = data.get("status").lower()
        tx_id = data.get("id")
        amount = Decimal(str(data.get("charged_amount") or data.get("amount")))

        if not tx_ref:
            logger.error("charge.completed webhook missing tx_ref")
            return {"status": "error", "detail": "missing tx_ref"}

        with db_transaction.atomic():
            try:
                tx = Transaction.objects.select_for_update().get(reference=tx_ref)
            except Transaction.DoesNotExist:
                logger.error(f"charge.completed: no transaction with ref={tx_ref}")
                return {"status": "error", "detail": "transaction not found"}

            if tx.status in (
                enums.TransactionStatus.SUCCESSFUL.value,
                enums.TransactionStatus.FAILED.value,
            ):
                logger.info(f"charge.completed: tx {tx_ref} already {tx.status}")
                return {
                    "status": "already_processed",
                    "detail": "charge already processed",
                }

            if flw_status != "successful":
                return PaymentHandlers._finalise_failed_charge(tx, data, flw_status)

        from core.payment.tasks import (
            verify_charge_and_initiate_subaccount_transfer_task,
        )

        verify_charge_and_initiate_subaccount_transfer_task.delay(
            tx_ref, tx_id, str(amount), data
        )
        return {
            "status": "queued",
            "detail": "charge verification and transfer queued",
        }

    @staticmethod
    def handle_transfer(data: dict) -> dict:
        """
        Handle Flutterwave 'transfer.completed' webhook.
        """
        tx_ref = data.get("reference")
        flw_status = data.get("status").lower()
        amount = Decimal(str(data.get("charged_amount") or data.get("amount")))
        tx_id = data.get("id")

        if not tx_ref:
            logger.error("transfer.completed webhook missing reference")
            return {"status": "error", "detail": "missing reference"}

        with db_transaction.atomic():
            try:
                tx = Transaction.objects.select_for_update().get(reference=tx_ref)
            except Transaction.DoesNotExist:
                logger.error(f"transfer.completed: no transaction with ref={tx_ref}")
                return {"status": "error", "detail": "transaction not found"}

            if tx.status in (
                enums.TransactionStatus.SUCCESSFUL.value,
                enums.TransactionStatus.FAILED.value,
            ):
                logger.info(f"transfer.completed: tx {tx_ref} already {tx.status}")
                return {"status": "already_processed"}

            if flw_status == "successful":
                from core.payment.tasks import verify_transfer_and_finalize_task

                verify_transfer_and_finalize_task.delay(
                    tx_ref, tx_id, str(amount), data
                )
                return {
                    "status": "queued",
                    "detail": "transfer verification and finalisation queued",
                }
            else:
                return PaymentHandlers._finalise_failed_transfer(tx, data, flw_status)
