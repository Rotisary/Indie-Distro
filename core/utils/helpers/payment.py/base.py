from loguru import logger
from decimal import Decimal

from core.payment.models import (
    LedgerAccount, 
    Transaction, 
    JournalEntry, 
    LedgerJournal
)
from core.users.models import User
from core.utils import enums
from core.utils.commons.utils.identifiers import ObjectIdentifiers




class PaymentLedgerCreatorHelpers:

    @staticmethod
    def get_or_create_ledger_account(
        user: User, type: str, currency: str="NGN"
    ) -> LedgerAccount:
        account, created = LedgerAccount.objects.get_or_create(
            owner=user,
            type=type,
            currency=currency
        )
        return account


    @staticmethod
    def create_ledger_transaction( 
            description: str = None, currency: str="NGN"
        ) -> Transaction:
        hex_id = ObjectIdentifiers.unique_hex_id()
        tx_reference = f"tx_{hex_id[:13]}"
        transaction = Transaction.objects.create(
            reference=tx_reference,
            status=enums.TransactionStatus.PENDING.value,
            description=description,
            currency=currency
        )
        return transaction
    

    @staticmethod
    def add_transaction_to_journal(
            transaction: Transaction
        ) -> LedgerJournal:
        journal, created = LedgerJournal.objects.get_or_create(
            transaction=transaction
        )
        return journal
    

    @staticmethod
    def create_ledger_entry(
            journal: LedgerJournal,
            account: LedgerAccount,
            entry_type: str,
            amount: Decimal,
            currency: str="NGN",
        ) -> JournalEntry:
        recent = (
            JournalEntry.objects.filter(journal=journal)
            .order_by("-created_at").first()
        )
        line_no = 0
        if not recent:
            line_no = 1
        else:
            line_no = recent.line_no + 1

        entry = JournalEntry.objects.create(
            journal=journal,
            account=account,
            line_no=line_no,
            type=entry_type,
            status=enums.EntryStatus.PENDING.value,
            amount=amount,
            currency=currency
        )
        return entry


class BasePaymentHelpers:

    @staticmethod
    def create_credit_and_debit_ledger_accounts(account_kwargs: dict) -> tuple:
        sender = account_kwargs.pop("sender")
        receiver = account_kwargs.pop("receiver")
        account_kwargs["user"] = sender
        debit_account = PaymentLedgerCreatorHelpers.get_or_create_ledger_account(**account_kwargs)
        account_kwargs["user"] = receiver
        credit_account = PaymentLedgerCreatorHelpers.get_or_create_ledger_account(**account_kwargs)
        return debit_account, credit_account