import mimetypes
import boto3
from loguru import logger

from django.conf import settings
from django.core.cache import cache
from rest_framework import status

from core.utils import exceptions
from core.utils.commons.utils import identifiers
from .base import BaseStorageHelper


class FileUploadUtils:
    """Utility class for handling file uploads to S3."""



    @staticmethod
    def save_file_metadata_in_memory(owner, file_id, file_key, expires_in):
        """
        Store file metadata in cache for a limited time. This is useful for tracking file uploads.
        """

        cache_key = f"pending_upload-{file_id}"
        cache_value = {
            "file_key": file_key,
            "owner": owner.id
        }
        cache.set(cache_key, cache_value, timeout=expires_in)
        return cache_key
    

    @staticmethod
    def get_file_key(owner, file_name, purpose):

        """Generate a unique file key for S3 storage."""

        owner_email = owner.email.lower()
        file_id = identifiers.ObjectIdentifiers.unique_id()

        if file_name:
            splitted_filename = file_name.split(".")
            if len(splitted_filename) > 1:
                extension = "." + splitted_filename[-1]
            else:
                extension = ""
        else:
            extension = ""

        file_key = f"uploads/{owner_email}/{purpose}/{file_id}{extension}"
        FileUploadUtils.save_file_metadata_in_memory(
            owner, file_id, file_key, expires_in=3600
        )
        data = {
            "file_id": file_id,
            "file_key": file_key
        }
        return data
    
    

    @staticmethod
    def generate_presigned_upload_url(file_key, file_name, expires_in=3600):
        """
        Generate a pre-signed URL for uploading to S3.
        file_key: the S3 key (path inside bucket)
        mime_type: MIME type (e.g. 'video/mp4')
        expires_in: link validity in seconds
        """

        assert(
            settings.USING_MANAGED_STORAGE
        ), "Cannot invoke this function when not using managed storage"
        try:
            storage_helper = BaseStorageHelper()
            
            presigned_url = storage_helper.s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                    "Key": file_key,
                    "ContentType": storage_helper.get_mime_type(file_name),
                },
                ExpiresIn=expires_in,
            )
        except Exception as e:
            logger.error(f"presigned url generation failed: {e}")
            raise exceptions.CustomException(
                message="presigned url generation failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        logger.info(f"presigned url generated successfully for {file_key}")
        return presigned_url