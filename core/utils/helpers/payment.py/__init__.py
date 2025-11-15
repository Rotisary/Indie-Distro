from decimal import Decimal

from django.db import transaction as db_transaction

from .base import *
from core.users.models import User
from core.utils import enums



class PostLedgerData:

    @staticmethod
    def as_pending(
        *,
        account_kwargs: dict,
        amount: Decimal,
        currency: str=None,
        description: str=None,
    ):
        with db_transaction.atomic():
            debit_account, credit_account = BasePaymentHelpers.create_credit_and_debit_ledger_accounts(
                account_kwargs
            )

            transaction = PaymentLedgerCreatorHelpers.create_ledger_transaction(
                description=description
            )

            journal = PaymentLedgerCreatorHelpers.add_transaction_to_journal(transaction)

            debit_entry = PaymentLedgerCreatorHelpers.create_ledger_entry(
                journal=journal, 
                account=debit_account, 
                entry_type=enums.EntryType.DEBIT.value,
                amount=amount
            )
            credit_entry = PaymentLedgerCreatorHelpers.create_ledger_entry(
                journal=journal, 
                account=credit_account, 
                entry_type=enums.EntryType.CREDIT.value,
                amount=amount               
            )
            return transaction

