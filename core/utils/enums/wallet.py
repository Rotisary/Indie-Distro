from .base import BaseEnum


class WalletCreationStatus(BaseEnum):
    PENDING = "pending"
    FAILED = "failed"
    RETRYING = "retrying"
    COMPLETED = "completed"


class WalletEventType(BaseEnum):
    WALLET_CREATED = "wallet_created"
    WALLET_RETRYING = "wallet_retrying"
    WALLET_FAILED = "wallet_failed"
    VIRTUAL_ACCOUNT_FETCHED = "virtual_account_fetched"
    VIRTUAL_ACCOUNT_RETRYING = "virtual_account_retrying"
    VIRTUAL_ACCOUNT_FAILED = "virtual_account_failed"
