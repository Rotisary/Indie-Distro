from typing import Any, Union
from rest_framework import status


class ClientPaymentException(Exception):
    def __init__(
        self,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        message: Union[int, str] = None,
        errors: Any = None,
    ):
        self.status_code = status_code
        self.message = message
        self.errors = errors