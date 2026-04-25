from datetime import timedelta
from decimal import Decimal

from django.db import transaction as db_transaction
from django.utils import timezone

from loguru import logger

from core.feed.models import Purchase
from core.payment.models import JournalEntry, Transaction
from core.utils import enums
from core.utils.helpers.payment import PostLedgerData
from core.wallet.models import Wallet
from core.webhook.models import ProviderWebhookEvent
from core.websocket.utils import emit_user_event

from .base import PaymentHelper


class PaymentHandlers:
    TRANSFER_WEBHOOK_EVENTS = (
        "transfer.completed",
        "transfer.disburse",
        "transfer.failed",
    )
    FINALIZED_STATES = (
        enums.TransactionFinalisationState.SUCCESS_FINALISED.value,
        enums.TransactionFinalisationState.FAILED_FINALISED.value,
    )
    NOT_FINALISED_STATES = (
        enums.TransactionFinalisationState.SUCCESS_NOT_FINALISED.value,
        enums.TransactionFinalisationState.FAILED_NOT_FINALISED.value,
        enums.TransactionFinalisationState.REFUND_REQUIRED.value,
        enums.TransactionFinalisationState.REFUND_PENDING.value,
        enums.TransactionFinalisationState.REFUND_FAILED.value,
    )

    @staticmethod
    def _extract_transfer_webhook_context(data: dict) -> dict:
        return {
            "tx_ref": data.get("reference") or data.get("tx_ref"),
            "bank_code": data.get("bank_code"),
            "account_number": data.get("account_number"),
            "tx_id": data.get("id"),
            "flw_status": (data.get("status") or "").lower(),
            "amount": Decimal(str(data.get("charged_amount") or data.get("amount"))),
        }

    @staticmethod
    def _transaction_is_finalized(tx: Transaction) -> bool:
        return tx.finalisation_state in PaymentHandlers.FINALIZED_STATES

    @staticmethod
    def _set_finalisation_state(tx: Transaction, state: str) -> None:
        if tx.finalisation_state == state:
            return

        tx.finalisation_state = state
        tx.save(update_fields=["finalisation_state", "date_last_modified"])

    @staticmethod
    def _set_provider_outcome(
        tx: Transaction, provider_outcome: str, payload: dict = None
    ) -> None:
        outcome = (provider_outcome or "").lower().strip()
        if not outcome:
            return

        metadata = tx.metadata or {}
        metadata["provider_outcome"] = {
            "status": outcome,
            "recorded_at": timezone.now().isoformat(),
            "payload": payload or {},
        }
        tx.metadata = metadata
        tx.save(update_fields=["metadata", "date_last_modified"])

    @staticmethod
    def _get_provider_outcome(tx: Transaction) -> tuple:
        webhook_event = (
            ProviderWebhookEvent.objects.filter(
                provider=enums.WebhookProvider.FLUTTERWAVE.value,
                tx_ref=tx.reference,
                event__in=PaymentHandlers.TRANSFER_WEBHOOK_EVENTS,
            )
            .order_by("-date_added")
            .first()
        )
        if webhook_event:
            payload = webhook_event.payload
            outcome = webhook_event.provider_status
            outcome = outcome.strip()
            if outcome:
                return outcome, payload

        metadata = tx.metadata or {}

        provider_outcome = metadata.get("provider_outcome") or {}
        outcome = (provider_outcome.get("status") or "").lower().strip()
        return outcome or None, provider_outcome.get("payload") or {}

    @staticmethod
    def _find_transaction_by_reference(tx_ref: str):
        if not tx_ref:
            return None

        tx = Transaction.objects.filter(reference=tx_ref).first()
        if tx:
            return tx

        return None

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

    @staticmethod
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
    def _create_virtual_funding_entry(data):
        context = PaymentHandlers._extract_transfer_webhook_context(data)
        tx_ref = context["tx_ref"]
        account_number = context["account_number"]
        amount = context["amount"]

        if not account_number:
            logger.info("transfer.completed: missing account number, using payout flow")
            return {
                "status": "error",
                "detail": f"account number is missing for tx_ref: {tx_ref}",
            }

        wallet = (
            Wallet.objects.select_related("owner")
            .filter(virtual_account_number=account_number)
            .first()
        )
        if not wallet:
            logger.info(
                f"transfer.completed: no wallet matched virtual account {account_number}, using payout flow"
            )
            return {"status": "error"}

        with db_transaction.atomic():
            entry_lines = [
                {
                    "user": wallet.owner,
                    "account_type": enums.LedgerAccountType.FUNDING.value,
                    "entry_type": enums.EntryType.DEBIT.value,
                    "amount": amount,
                },
                {
                    "user": wallet.owner,
                    "account_type": enums.LedgerAccountType.USER_WALLET.value,
                    "entry_type": enums.EntryType.CREDIT.value,
                    "amount": amount,
                },
            ]
            tx = PostLedgerData.as_pending(
                ledger_data=entry_lines,
                tx_purpose=enums.TransactionPurpose.FUNDING.value,
                type=enums.PaymentType.TRANSFER.value,
                description="Wallet funding via static virtual account",
            )
        return tx

    @staticmethod
    def _post_successful_charge(tx: Transaction, data: dict, flw_status: str):
        try:
            PostLedgerData.as_successful(tx, data, "charge")
            return True
        except Exception as e:
            # TODO issue refund
            logger.warning(
                f"charge.completed: tx {tx.reference} success posting failed"
            )
            PaymentHandlers._finalise_failed_charge(
                tx,
                data,
                flw_status,
                state=enums.TransactionFinalisationState.SUCCESS_NOT_FINALISED.value,
            )
            return False

    @staticmethod
    def _finalise_failed_charge(
        tx: Transaction,
        data: dict,
        flw_status: str,
        state: str = enums.TransactionFinalisationState.FAILED_NOT_FINALISED.value,
    ) -> dict:
        PaymentHandlers._set_provider_outcome(tx, flw_status, data)
        try:
            with db_transaction.atomic():
                PostLedgerData.as_failed(tx, data, "charge")
                PaymentHandlers._mark_purchase_failed(tx)
                db_transaction.on_commit(
                    lambda: PaymentHandlers._emit_payment_event(tx, success=False)
                )
            logger.warning(f"charge.completed: tx {tx.reference} failed ({flw_status})")
            return {"status": "failed"}
        except Exception as failed_post_err:
            PaymentHandlers._set_finalisation_state(tx, state)
            logger.error(
                f"charge.completed: tx {tx.reference} failed-posting also failed: {str(failed_post_err)}"
            )
            return {"status": "failed", "detail": "reconciliation required"}

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
                type=enums.PaymentType.TRANSFER.value,
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
    def _finalise_successful_transfer(
        tx: Transaction, data: dict, amount, flw_status: str
    ) -> dict:
        """
        Finalises successful transfers and move money from and to  the right balances
        """
        try:
            with db_transaction.atomic():
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
                    raise ValueError("missing credit entry")

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

                db_transaction.on_commit(
                    lambda: PaymentHandlers._emit_payment_event(
                        tx, success=True, amount=amount
                    )
                )
            logger.success(
                f"transfer.completed: tx {tx.reference} finalised ({tx_purpose})"
            )
            return {"status": "success"}
        except Exception as e:
            logger.warning(
                f"transfer.completed: tx {tx.reference} success finalization failed: {str(e)}"
            )
            return PaymentHandlers._finalise_failed_transfer(
                tx,
                data,
                flw_status,
                state=enums.TransactionFinalisationState.SUCCESS_NOT_FINALISED.value,
            )

    @staticmethod
    def _finalise_failed_transfer(
        tx: Transaction,
        data: dict,
        flw_status: str,
        state: str = enums.TransactionFinalisationState.FAILED_NOT_FINALISED.value,
    ) -> dict:
        PaymentHandlers._set_provider_outcome(tx, flw_status, data)
        try:
            with db_transaction.atomic():
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
                    raise ValueError("missing debit entry")

                if debit_entry.account.owner is not None:
                    wallet = debit_entry.account.owner.wallet
                    if tx.purpose == enums.TransactionPurpose.PAYOUT.value:
                        wallet.pay_to_wallet(debit_entry.amount)
                    elif tx.purpose == enums.TransactionPurpose.PURCHASE.value:
                        wallet.pay_to_wallet(debit_entry.amount, is_funding=True)
                        PaymentHandlers._mark_purchase_failed(
                            tx.parent_transaction if tx.parent_transaction else tx
                        )

                db_transaction.on_commit(
                    lambda: PaymentHandlers._emit_payment_event(
                        tx, success=False, amount=debit_entry.amount
                    )
                )
            logger.warning(
                f"transfer.completed: tx {tx.reference} failed ({flw_status})"
            )
            return {"status": "failed"}
        except Exception as failed_post_err:
            PaymentHandlers._set_finalisation_state(tx, state)
            logger.error(
                f"transfer.completed: tx {tx.reference} failed-posting also failed: {str(failed_post_err)}"
            )
            return {"status": "failed", "detail": "reconciliation required"}

    @staticmethod
    def handle_transfer_event(data: dict) -> dict:
        context = PaymentHandlers._extract_transfer_webhook_context(data)
        tx_ref = context["tx_ref"]

        if not tx_ref:
            logger.error("transfer.completed webhook missing reference")
            return {"status": "error", "detail": "missing reference"}

        existing_tx = PaymentHandlers._find_transaction_by_reference(tx_ref)
        if existing_tx:
            if PaymentHandlers._transaction_is_finalized(existing_tx):
                logger.info(
                    f"transfer.completed: tx {existing_tx.reference} already {existing_tx.status}"
                )
                return {"status": "already_processed"}

            return PaymentHandlers.handle_transfer(data, existing_tx)

        return PaymentHandlers.handle_virtual_account_funding(data)

    @staticmethod
    def handle_virtual_account_funding(data: dict) -> dict:
        from core.payment.tasks import handle_virtual_funding_task

        context = PaymentHandlers._extract_transfer_webhook_context(data)
        handle_virtual_funding_task.delay(
            context["tx_ref"], context["tx_id"], str(context["amount"]), data
        )
        return {
            "status": "queued",
            "detail": "transfer verification and finalisation queued",
        }

    @staticmethod
    def handle_bank_charge(data: dict) -> dict:
        """
        Handle Flutterwave 'charge.completed' webhook.
        """
        context = PaymentHandlers._extract_transfer_webhook_context(data)
        tx_ref = context["tx_ref"]

        if not tx_ref:
            logger.error("charge.completed webhook missing tx_ref")
            return {"status": "error", "detail": "missing tx_ref"}

        existing_tx = PaymentHandlers._find_transaction_by_reference(tx_ref)
        if not existing_tx:
            logger.error(f"charge.completed: no transaction with ref={tx_ref}")
            return {"status": "error", "detail": "transaction not found"}

        if PaymentHandlers._transaction_is_finalized(existing_tx):
            logger.info(f"charge.completed: tx {tx_ref} already {existing_tx.status}")
            return {
                "status": "already_processed",
                "detail": "charge already processed",
            }

        from core.payment.tasks import (
            verify_charge_and_initiate_subaccount_transfer_task,
        )

        verify_charge_and_initiate_subaccount_transfer_task.delay(
            tx_ref, context["tx_id"], str(context["amount"]), data
        )
        return {
            "status": "queued",
            "detail": "charge verification and transfer queued",
        }

    @staticmethod
    def handle_transfer(data: dict, tx: Transaction) -> dict:
        """
        Handle Flutterwave 'transfer.completed' webhook.
        """
        context = PaymentHandlers._extract_transfer_webhook_context(data)

        from core.payment.tasks import verify_transfer_and_finalize_task

        verify_transfer_and_finalize_task.delay(
            tx.reference, context["tx_id"], str(context["amount"]), data
        )
        return {
            "status": "queued",
            "detail": "transfer verification and finalisation queued",
        }

    @staticmethod
    def reconcile_transaction_finalization(tx_ref: str) -> dict:
        with db_transaction.atomic():
            tx = (
                Transaction.objects.select_for_update().filter(reference=tx_ref).first()
            )
            if not tx:
                return {"status": "not_found", "tx_ref": tx_ref}

            if PaymentHandlers._transaction_is_finalized(tx):
                return {"status": "already_processed", "tx_ref": tx_ref}

            provider_outcome, payload = PaymentHandlers._get_provider_outcome(tx)
            if not provider_outcome:
                return {
                    "status": "skipped",
                    "tx_ref": tx_ref,
                    "detail": "provider outcome unavailable",
                }

            if tx.type == enums.PaymentType.BANK_CHARGE.value:
                result = PaymentHandlers._finalise_failed_charge(
                    tx,
                    {
                        "webhook": payload,
                        "provider_outcome": provider_outcome,
                        "reconciled": True,
                    },
                    provider_outcome,
                )
            else:
                result = PaymentHandlers._finalise_failed_transfer(
                    tx,
                    {
                        "webhook": payload,
                        "provider_outcome": provider_outcome,
                        "reconciled": True,
                    },
                    provider_outcome,
                )
            return {"tx_ref": tx_ref, **result}
