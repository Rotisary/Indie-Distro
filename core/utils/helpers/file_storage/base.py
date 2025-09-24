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
    

    def generate_presigned_get_url(self, file_key, expires_in=3600):
        """
        Generate a pre-signed URL to get a file from S3.
        file_key: the S3 key (path inside bucket)
        expires_in: link validity in seconds
        """

        assert(
            settings.USING_MANAGED_STORAGE
        ), "Cannot invoke this function when not using managed storage"
        try:          
            presigned_url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                    "Key": file_key,
                },
                ExpiresIn=expires_in,
            )
        except Exception as e:
            logger.error(f"presigned url generation failed: {e}")
            raise exceptions.CustomException(
                message="presigned url generation failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return presigned_url

