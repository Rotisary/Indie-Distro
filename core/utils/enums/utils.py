from .base import BaseEnum


class ModelNameChoice(BaseEnum):
    FILM = "Feed"
    SHORT = "Short"


class KeyProcessStatus(BaseEnum):
    IN_PROGRESS = "in progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"