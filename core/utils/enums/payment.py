from .base import BaseEnum


class SupportedCurrency(BaseEnum):
    NGN = "NGN"
    USD = "USD"
    EUR = "EUR"


class LedgerAccountType(BaseEnum):
    USER_WALLET = "user wallet"
    PROVIDER_WALLET = "provider wallet"
    SALES_FEE = "sales fee"
    FUNDING = "funding"
    WITHDRAWAL = "withdrawal"
    EXTERNAL_PAYMENT = "external payment"


class TransactionStatus(BaseEnum):
    PENDING = "Pending"
    INITIATED = "Initiated"
    SUCCESSFUL = "Successful"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    REVERSED = "Reversed"


class EntryStatus(BaseEnum):
    PENDING = "Pending"
    COMPLETED = "Completed"
    FAILED = "Failed"


class EntryType(BaseEnum):
    CREDIT = "Credit"
    DEBIT = "Debit"


class PaymentType(BaseEnum):
    BANK_CHARGE = "bank_charge"
    TRANSFER = "transfer"


class TransactionPurpose(BaseEnum):
    PAYOUT = "payment"
    PURCHASE = "purchase"
    FUNDING = "funding"


class PaymentEventType(BaseEnum):
    PURCHASE_SUCCEEDED = "purchase_succeeded"
    PURCHASE_FAILED = "purchase_failed"
    FUNDING_SUCCEEDED = "funding_succeeded"
    FUNDING_FAILED = "funding_failed"
    PAYOUT_SUCCEEDED = "payout_succeeded"
    PAYOUT_FAILED = "payout_failed"
