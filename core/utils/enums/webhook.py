from .base import BaseEnum


class WebhookEvent(BaseEnum):
    PROCESSING_COMPLETED = "processing_complete"
    PROCESSING_FAILED = "processing_failed"
    WALLET_CREATION_COMPLETED = "wallet_creation_completed"
    WALLET_CREATION_FAILED = "wallet_creation_failed"