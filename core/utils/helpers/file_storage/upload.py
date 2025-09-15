import mimetypes
import boto3
from django.conf import settings

from core.utils.commons.utils import identifiers


class FileUploadUtils:
    """Utility class for handling file uploads to S3."""


    @staticmethod
    def get_file_key(owner, file_name, purpose):

        """Generate a unique file key for S3 storage."""

        owner_email = owner.email.lower()
        file_id = identifiers.ObjectIdentifiers.unique_id

        if file_name:
            splitted_filename = file_name.split(".")
            if len(splitted_filename) > 1:
                extension = "." + splitted_filename[-1]
            else:
                extension = ""
        else:
            extension = ""

        return f"uploads/{owner_email}/{purpose}/{file_id}{extension}"
    

    @staticmethod
    def get_mime_type(file_name):

        """Determine the MIME type of a file based on its name."""

        mime_type, *_ = mimetypes.guess_type(file_name)
        return mime_type if mime_type else "application/octet-stream"
    

    @staticmethod
    def generate_presigned_url(file_key, mime_type, expires_in=3600):
        """
        Generate a pre-signed URL for uploading to S3.
        file_key: the S3 key (path inside bucket)
        mime_type: MIME type (e.g. 'video/mp4')
        expires_in: link validity in seconds
        """
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        
        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": file_key,
                "ContentType": mime_type,
            },
            ExpiresIn=expires_in,
        )

        return presigned_url