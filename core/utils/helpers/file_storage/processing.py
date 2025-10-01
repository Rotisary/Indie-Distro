import subprocess
import json
import shutil

from loguru import logger

from rest_framework import status

from .base import StorageUtils
from core.utils import exceptions


class FileProcessingUtils:

    @staticmethod
    def ffprobe_get_json(file_url):
        """
        Run ffprobe on 'file key' (presigned URL) and return parsed JSON.
        """

        StorageUtils.ensure_binary_on_path("ffprobe")
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_format",
            "-show_streams",
            "-print_format", "json",
            file_url,
        ]       
        stdout = StorageUtils.run_cmd(cmd)
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            logger.error("ffprobe returned invalid JSON: {}", stdout[:200])
            raise exceptions.CustomException(
                message="ffprobe returned invalid JSON",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
