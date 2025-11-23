from decimal import Decimal

from django.db import transaction as db_transaction

from .base import *



class PostLedgerData:

    @staticmethod
    def as_pending(
        ledger_data: list[dict],
        currency: str=None,
        description: str=None,
    ):
        with db_transaction.atomic():
            transaction = PaymentLedgerCreatorHelpers.create_ledger_transaction(
                description=description
            )
            journal = PaymentLedgerCreatorHelpers.add_transaction_to_journal(transaction)
            for data in ledger_data: 
                ledger_account = PaymentLedgerCreatorHelpers.get_or_create_ledger_account(
                    user=data["user"], type=data["account_type"]
                )
                ledger_entry = PaymentLedgerCreatorHelpers.create_ledger_entry(
                    journal=journal, 
                    account=ledger_account, 
                    entry_type=data["entry_type"],
                    amount=data["amount"]
                )
            return transaction

