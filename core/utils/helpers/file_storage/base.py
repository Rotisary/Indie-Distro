import boto3
import mimetypes
from loguru import logger

from rest_framework import status
from django.conf import settings

from core.utils import exceptions




class BaseStorageHelper:
    """
    helper class that contains all base storage utilities(utilities to be reused across the codebase)
    """

    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )


    @staticmethod
    def get_mime_type(file_name):

        """Determine the MIME type of a file based on its name."""

        mime_type, *_ = mimetypes.guess_type(file_name)
        return mime_type if mime_type else "application/octet-stream"

