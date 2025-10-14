from .base import BaseEnum


class WebhookEvent(BaseEnum):
    PROCESSING_COMPLETED = "processing_complete"
    PROCESSING_FAILED = "processing_failed"