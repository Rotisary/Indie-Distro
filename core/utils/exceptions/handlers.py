from loguru import logger

from .base import ServiceRequestException


class Handlers:

    @staticmethod
    def handle_request_failure(response, message):
        if int(response.status_code) >= 300:
            logger.error(message)
            raise ServiceRequestException(
                message=message,
                errors=[f"{response.text}"],
                status_code=response.status_code
            )