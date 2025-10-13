from .base import BaseEnum


class WebhookEvent(BaseEnum):
    PROCESSING_COMPLETE = "processing_complete"
    PROCESSING_FAILED = "processing_failed"