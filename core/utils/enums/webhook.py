from .base import BaseEnum


class WebhookEvent(BaseEnum):
    PROCESSING_COMPLETED = "processing_complete"
    PROCESSING_FAILED = "processing_failed"
    WALLET_CREATION_COMPLETED = "wallet_creation_completed"
    WALLET_CREATION_FAILED = "wallet_creation_failed"
    FUNDING_COMPLETED = "funding_completed"
    FUNDING_FAILED = "funding_failed"
    BANK_CHARGE_INITIATED = "bank_charge_initiated"
    BANK_CHARGE_INITIATION_FAILED = "bank_charge_initiation_failed"