import boto3
import mimetypes
import hashlib
import os
import shutil
import subprocess
import tempfile
from typing import Iterable, Optional, Tuple

from loguru import logger

from rest_framework import status
from django.conf import settings

from core.utils import exceptions

# Register common streaming types; for use in file processing
mimetypes.init()
mimetypes.add_type("application/vnd.apple.mpegurl", ".m3u8", strict=True)
mimetypes.add_type("video/mp2t", ".ts", strict=True)
mimetypes.add_type("application/dash+xml", ".mpd", strict=True)
mimetypes.add_type("video/iso.segment", ".m4s", strict=True)


class StorageClient:
    """
    s3 client class. Contains all base methods that involves s3 clients
    """

    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
            endpoint_url=settings.AWS_S3_ENDPOINT_URL
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


    def upload_file_to_s3(self, local_path: str, key: str, content_type: Optional[str] = None) -> None:
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        extra = {}
        if content_type:
            extra["ContentType"] = content_type
        logger.info(f"Uploading {local_path} -> s3://{bucket}/{key}")
        self.s3_client.upload_file(local_path, bucket, key, ExtraArgs=extra or None)
    

class StorageUtils:

    @staticmethod
    def ensure_binary_on_path(binary: str):
        if shutil.which(binary) is None:
            logger.error("{} binary not found on PATH", binary)
            raise exceptions.CustomException(
                message=f"{binary} not available on server",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
    @staticmethod
    def run_cmd(cmd: Iterable[str], timeout: int = 3600) -> str:
        """
        Run a command safely; return (stdout, stderr). Raise on failure.
        """

        logger.info(f"Running command: {cmd}")
        try:
            response = subprocess.run(
                list(cmd),
                capture_output=True,
                text=True,
                check=True,
                timeout=timeout,
            )
            return response.stdout or ""
        except subprocess.CalledProcessError as e:
            logger.error(
                "command failed: returncode={}, stderr={}",
                getattr(e, "returncode", None),
                getattr(e, "stderr", None),
            )
            raise exceptions.CustomException(
                message="command processing failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except subprocess.TimeoutExpired as e:
            logger.error(f"command timed out after {timeout} seconds: {e}")
            raise exceptions.CustomException(
                message="command timed out",
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except Exception as e:
            logger.exception(f"unexpected error running command: {e}")
            raise exceptions.CustomException(
                message="unexpected error running command",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
    
    @staticmethod
    def make_tempdir(prefix: str = "proc-") -> str:
        return tempfile.mkdtemp(prefix=prefix)