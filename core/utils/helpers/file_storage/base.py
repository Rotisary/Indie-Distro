import mimetypes
import os
import shutil
import subprocess
import tempfile
import time
from typing import Iterable, Optional

from django.conf import settings

import boto3
from botocore.exceptions import (
    ConnectionClosedError,
    ConnectTimeoutError,
    EndpointConnectionError,
    ReadTimeoutError,
)
from loguru import logger
from rest_framework import status

from core.file_storage.models import FileProcessingJob
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
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
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

        assert (
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
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return presigned_url

    def upload_file_to_s3(
        self, local_path: str, key: str, content_type: Optional[str] = None, **kwargs
    ) -> None:
        assert settings.USING_MANAGED_STORAGE, "Managed storage must be enabled"
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        extra = {}
        if content_type:
            extra["ContentType"] = content_type

        def _upload():
            logger.info(f"Uploading {local_path} -> s3://{bucket}/{key}")
            self.s3_client.upload_file(local_path, bucket, key, ExtraArgs=extra or None)

        def _on_retry(exc, attempt, delay):
            logger.warning(
                f"Upload retry {attempt} in {delay}s for s3://{bucket}/{key}: {exc}"
            )

        try:
            StorageUtils._retry_operation(
                _upload,
                retries=2,
                delays=(10, 15),
                retry_on=(
                    EndpointConnectionError,
                    ConnectTimeoutError,
                    ReadTimeoutError,
                    ConnectionClosedError,
                ),
                on_retry=_on_retry,
                job=kwargs.get("job"),
            )
        except Exception as e:
            message = f"upload failed for {local_path} -> s3://{bucket}/{key}: {e}"
            logger.error(message)
            StorageUtils._handle_job_failure(kwargs, message)
            raise exceptions.CustomException(
                message="upload to storage failed",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

    def download_file_from_s3(self, key: str, local_path: str, **kwargs) -> str:
        """
        Download an object from S3/Spaces to a local file path (creates parent dirs).
        Returns the local_path on success.
        """
        assert settings.USING_MANAGED_STORAGE, "Managed storage must be enabled"
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        def _download():
            logger.info(f"Downloading s3://{bucket}/{key} -> {local_path}")
            self.s3_client.download_file(bucket, key, local_path)

        def _on_retry(exc, attempt, delay):
            logger.warning(
                f"Download retry {attempt} in {delay}s for s3://{bucket}/{key}: {exc}"
            )

        try:
            StorageUtils._retry_operation(
                _download,
                retries=2,
                delays=(10, 15),
                retry_on=(
                    EndpointConnectionError,
                    ConnectTimeoutError,
                    ReadTimeoutError,
                    ConnectionClosedError,
                ),
                on_retry=_on_retry,
                job=kwargs.get("job"),
            )
            return local_path
        except Exception as e:
            message = f"download failed for s3://{bucket}/{key}: {e}"
            logger.error(message)
            StorageUtils._handle_job_failure(kwargs, message)
            raise exceptions.CustomException(
                message=message,
                status_code=status.HTTP_502_BAD_GATEWAY,
            )


class StorageUtils:
    "Utility helpers for managed storage processes"

    @staticmethod
    def _retry_operation(
        func,
        *,
        retries: int,
        delays: Iterable[int],
        retry_on: tuple,
        on_retry=None,
        job: FileProcessingJob = None,
    ):
        attempt = 0
        while True:
            try:
                return func()
            except retry_on as exc:
                if attempt >= retries:
                    raise
                delay_list = list(delays)
                delay = 0
                if delay_list:
                    delay = delay_list[min(attempt, len(delay_list) - 1)]
                attempt += 1
                if job is not None:
                    job.mark_retrying(attempt=attempt, reason=str(exc))
                if on_retry:
                    on_retry(exc, attempt, delay)
                if delay:
                    time.sleep(delay)

    @staticmethod
    def _handle_job_failure(kwargs: dict, message: str) -> None:
        job: FileProcessingJob = kwargs.get("job", None)
        if job is not None:
            job.mark_failed(message)

    @staticmethod
    def ensure_binary_on_path(binary: str, **kwargs):
        if shutil.which(binary) is None:
            message = f"{binary} not available on server"
            logger.error(message)
            StorageUtils._handle_job_failure(kwargs, message)
            raise exceptions.CustomException(
                message=message,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @staticmethod
    def run_cmd(
        cmd: Iterable[str], timeout: int = 3600, cwd: Optional[str] = None, **kwargs
    ) -> str:
        """
        Run a command safely; return (stdout, stderr). Raise on failure.
        """

        logger.info(f"Running command: {cmd}")
        if cwd:
            logger.info(f"Working directory: {cwd}")

        def _run():
            return subprocess.run(
                list(cmd),
                capture_output=True,
                text=True,
                check=True,
                timeout=timeout,
                cwd=cwd,
            )

        def _on_retry(exc, attempt, delay):
            logger.warning(f"Command retry {attempt} in {delay}s: {cmd} ({exc})")

        try:
            response = StorageUtils._retry_operation(
                _run,
                retries=2,
                delays=(10, 15),
                retry_on=(subprocess.TimeoutExpired,),
                on_retry=_on_retry,
                job=kwargs.get("job"),
            )
            return response.stdout or ""
        except subprocess.CalledProcessError as e:
            message = (
                "command failed: returncode={}, stderr={}",
                getattr(e, "returncode", None),
                getattr(e, "stderr", None),
            )
            logger.error(message)
            StorageUtils._handle_job_failure(kwargs, message)
            raise exceptions.CustomException(
                message="command processing failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except subprocess.TimeoutExpired as e:
            message = f"command timed out after {timeout} seconds: {e}"
            logger.error(message)
            StorageUtils._handle_job_failure(kwargs, message)
            raise exceptions.CustomException(
                message=message,
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except Exception as e:
            message = f"unexpected error running command: {e}"
            logger.exception(message)
            StorageUtils._handle_job_failure(kwargs, message)
            raise exceptions.CustomException(
                message="unexpected error running command",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @staticmethod
    def make_tempdir(prefix: str = "proc-") -> str:
        return tempfile.mkdtemp(prefix=prefix)

    @staticmethod
    def get_job_workdir(job_id: int) -> str:
        """
        Deterministic per-job workspace.
        Persists across tasks and is deleted in finalize.
        """
        job_dir = os.path.join(settings.BASE_DIR, "jobs", str(job_id))
        os.makedirs(job_dir, exist_ok=True)
        return job_dir

    @staticmethod
    def ensure_dir(path: str) -> str:
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def cleanup_job_workdir(job_id: int) -> None:
        job_dir = os.path.join(settings.BASE_DIR, "jobs", str(job_id))
        try:
            shutil.rmtree(job_dir, ignore_errors=True)
            logger.info(f"Cleaned workspace: {job_dir}")
        except Exception:
            logger.warning(f"Failed to cleanup workspace: {job_dir}")
