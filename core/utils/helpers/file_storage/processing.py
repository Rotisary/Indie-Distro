import subprocess
import json
import shutil

from loguru import logger

from rest_framework import status

from .base import BaseStorageHelper
from core.utils import exceptions


class FileProcessingUtils:

    @staticmethod
    def ffprobe_get_json(file_url, timeout=30):
        """
        Run ffprobe on 'file key' (presigned URL) and return parsed JSON.
        """

        # make sure ffprobe binary is available
        if shutil.which("ffprobe") is None:
            logger.error("ffprobe binary not found on PATH")
            raise exceptions.CustomException(
                message="ffprobe binary not available on server",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_format",
            "-show_streams",
            "-print_format", "json",
            file_url,
        ]
        
        try:
            response = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,      
                timeout=timeout,
            )
        except subprocess.CalledProcessError as e:
            logger.error(
                "ffprobe failed: returncode={}, stderr={}",
                getattr(e, "returncode", None),
                getattr(e, "stderr", None),
            )
            raise exceptions.CustomException(
                message="ffprobe processing failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except subprocess.TimeoutExpired as e:
            logger.error("ffprobe timed out after {} seconds: {}", timeout, e)
            raise exceptions.CustomException(
                message="ffprobe timed out",
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except Exception as e:
            logger.exception("unexpected error running ffprobe: {}", e)
            raise exceptions.CustomException(
                message="unexpected error running ffprobe",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        stdout = response.stdout or ""
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            logger.error("ffprobe returned invalid JSON: {}", stdout[:200])
            raise exceptions.CustomException(
                message="ffprobe returned invalid JSON",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# FileProcessingUtils.ffprobe_get_json("uploads/oladotunkolapo@gmail.com/main_file/8c9f56d5e11758875216.mp4")