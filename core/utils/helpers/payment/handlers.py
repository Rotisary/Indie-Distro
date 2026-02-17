from loguru import logger
from decimal import Decimal

from django.db import transaction as db_transaction

from core.payment.models import Transaction, JournalEntry
from core.wallet.models import Wallet
from core.utils import enums
from core.utils.helpers.payment import PostLedgerData
from .base import PaymentHelper


class PaymentHandlers:

    @staticmethod
    def handle_bank_charge(data: dict) -> dict:
        """
        Handle Flutterwave 'charge.completed' webhook.
        """
        tx_ref = data.get("tx_ref")
        flw_status = data.get("status").lower()
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
                return {"status": "already_processed"}

            if flw_status != "successful":
                return PaymentHandlers._finalise_failed_charge(tx, data, flw_status)

            # Verify with Flutterwave before proceeding
            # if flw_id and not PaymentHandler._verify_charge(flw_id, tx.amount, tx.currency):
            #     logger.error(f"Charge verification failed for tx {tx_ref}")
            #     return PaymentHandler._finalise_failed_charge(tx, data, "verification_failed")

            PostLedgerData.as_successful(tx, data, "charge")

        from core.payment.tasks import initiate_subaccount_transfer_task
        initiate_subaccount_transfer_task.delay(tx.reference, amount)

        return {"status": "success", "detail": "charge verified, transfer initiated"}
    

    @staticmethod
    def handle_transfer(data: dict) -> dict:
        """
        Handle Flutterwave 'transfer.completed' webhook.
        """
        tx_ref = data.get("reference")
        flw_status = data.get("status").lower()
        amount = Decimal(str(data.get("charged_amount") or data.get("amount")))

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
                return PaymentHandlers._finalise_successful_transfer(tx, data, amount)
            else:
                return PaymentHandlers._finalise_failed_transfer(tx, data, flw_status)
    

    @staticmethod
    def _finalise_failed_charge(tx: Transaction, data: dict, flw_status: str) -> dict:
        PostLedgerData.as_failed(tx, data, "charge")
        logger.warning(f"charge.completed: tx {tx.reference} failed ({flw_status})")

        return {"status": "failed"}


    @staticmethod
    def _initiate_subaccount_transfer(charge_tx: Transaction, amount) -> None:
        """
        After a successful bank charge, transfer funds from the main
        Flutterwave account into the user's payout subaccount.
        """
    
        debit_entry = (
            JournalEntry.objects
            .filter(
                journal__transaction=charge_tx,
                type=enums.EntryType.DEBIT.value,
                account__type=enums.LedgerAccountType.FUNDING.value,
            )
            .select_related("account__owner")
            .first()
        )

        if not debit_entry:
            logger.error(
                f"No USER_WALLET credit entry for charge tx {charge_tx.reference}; "
                "cannot determine user for subaccount transfer"
            )
            return {"status": "error", "detail": "missing debit entry"}

        user = debit_entry.account.owner
        
        entry_lines = [
            {
                "user": None,
                "account_type": enums.LedgerAccountType.PROVIDER_WALLET.value,
                "entry_type": enums.EntryType.DEBIT.value,
                "amount": amount
            },
            {
                "user": user,
                "account_type": enums.LedgerAccountType.USER_WALLET.value,
                "entry_type": enums.EntryType.CREDIT.value,
                "amount": amount
            }
        ]

        with db_transaction.atomic():
            transaction = PostLedgerData.as_pending(
                ledger_data=entry_lines,
                description="bank charge completion via subaccount transfer"
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
            JournalEntry.objects
            .filter(
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
        elif tx.purpose == enums.TransactionPurpose.PAYOUT.value:
            wallet.withdraw_funds(amount, is_earnings=True)

        logger.success(f"transfer.completed: tx {tx.reference} finalised ({tx_purpose})")
        return {"status": "success"}

    @staticmethod
    def _finalise_failed_transfer(tx: Transaction, data: dict, flw_status: str) -> dict:

        PostLedgerData.as_failed(tx, data, "transfer")
        debit_entry = (
            JournalEntry.objects
            .filter(
                journal__transaction=tx,
                type=enums.EntryType.DEBIT.value
            )
            .select_related("account__owner")
            .first()
        )
        if not debit_entry:
            logger.error(
                f"No debit entry for transfer tx {tx.reference} found"
            )
            return {"status": "error", "detail": "missing debit entry"}
        
        wallet = debit_entry.account.owner.wallet
        if tx.purpose == enums.TransactionPurpose.PURCHASE.value:   
            wallet.pay_to_wallet(debit_entry.amount, is_funding=True)
        elif tx.purpose == enums.TransactionPurpose.PAYOUT.value:
            wallet.pay_to_wallet(debit_entry.amount)

        logger.warning(f"transfer.completed: tx {tx.reference} failed ({flw_status})")
        return {"status": "failed"}
