from .base import BaseEnum


class WalletCreationStatus(BaseEnum):
    PENDING = "pending"
    FAILED = "failed"
    COMPLETED = "completed"