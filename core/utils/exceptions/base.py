from typing import Any, Union
from django.core.exceptions import ValidationError as DjangoCoreValidationError
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed


class CustomException(Exception):
    def __init__(
        self,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        message: Union[int, str] = None,
        errors: Any = None,
    ):
        self.status_code = status_code
        self.message = message
        self.errors = errors



class QuerySetException(Exception):
    def __init__(self, errors: list, message: str):
        self.errors = errors
        self.message = message


class ServiceRequestException(Exception):

    def __init__(
            self,
            message: str,
            errors: list[str] = None, 
            status_code: int = status.HTTP_400_BAD_REQUEST
        ):
        self.status_code = status_code
        self.errors = errors
        self.message = message