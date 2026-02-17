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
