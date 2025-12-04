from loguru import logger
from decimal import Decimal
from dataclasses import dataclass
from requests import RequestException

from core.payment.models import (
    LedgerAccount, 
    Transaction, 
    JournalEntry, 
    LedgerJournal
)
from core.users.models import User
from core.utils import enums
from core.utils.commons.utils.identifiers import ObjectIdentifiers
from core.utils.services import FlutterwaveService
from core.utils.exceptions import exceptions
 


class PaymentHelper:

    def __init__(
            self, 
            user: User, 
            transaction: Transaction,
            amount: Decimal,
            payment_type: str,
            *,
            charge_type: str = None,
        ):
        self.user = user
        self.payment_type = payment_type
        self.transaction = transaction
        self.amount = amount

        if payment_type == enums.PaymentType.BANK_CHARGE:
            if not charge_type:
                raise ValueError("charge_type required for BANK_CHARGE")
            self.charge_type = charge_type
        else:
            if charge_type:
                raise ValueError("charge_type only allowed for BANK_CHARGE")
            self.charge_type = None

    @dataclass
    class PaymentResponse:
        status: str
        data: dict = None
        error: str = None
        message: str = None


    def charge_bank(self) -> PaymentResponse:
        return getattr(self, f"charge_{self.charge_type.lower()}_account")()


    def charge_nigerian_account(self) -> PaymentResponse:
        try:
            service = FlutterwaveService()
            data = service.charge_nigerian_bank(
                user=self.user,
                amount=self.amount,
                tx_reference=self.transaction.reference
            )
            logger.success("nigerian bank charge initiated")
            self.transaction.status = enums.TransactionStatus.INITIATED.value
            self.transaction.metadata = data
            self.transaction.save(update_fields=["status", "metadata"])
            return self.PaymentResponse(
                status="initiated", data=data["meta"]["authorization"]
            )
        except (
            RequestException,
            exceptions.ServiceRequestException,
            exceptions.CustomException, 
            exceptions.ClientPaymentException
        ) as exc:
            logger.error(f"nigerian account charge failed ({self.transaction.reference}): {str(exc)}")
            return self.PaymentResponse(
                status="failed", error=exc.errors, message=exc.message
            )       


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
