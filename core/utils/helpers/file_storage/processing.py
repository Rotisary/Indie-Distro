import json
import os

from loguru import logger
from typing import Any, Dict

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from rest_framework import status

from .base import StorageUtils, StorageClient
from core.utils import exceptions


class FileProcessingUtils:

    @staticmethod
    def ffprobe_get_json(file):
        """
        Run ffprobe on source file and return parsed JSON.
        """

        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_format",
            "-show_streams",
            "-print_format", "json",
            file,
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
        
    @staticmethod
    def update_obj_fields(
        instance: models.Model,
        updates: Dict[str, Any],
        *,
        validate: bool = True,
        save: bool = True,
    ) -> Dict[str, bool]:
        """
        updates multiple or single fields, skipping unknown ones.
        Returns a dict of {field_name: True/False}.
        Does not accept M2M fields, ForeignKey fields and OneToOne fields
        """
        results = {}
        normal_fields = ["date_last_modified", ]
        for name, val in updates.items():
            try:
                field = instance._meta.get_field(name)
            except FieldDoesNotExist:
                results[name] = False
                continue

            results[name] = True
            # attempt to coerce value to python type
            try:
                python_value = field.to_python(val)
            except Exception:
                python_value = val
    
            setattr(instance, name, python_value)
            normal_fields.append(name)
 

        # if validate and normal_fields:
        #     instance.full_clean(validate_fields=normal_fields)
        if save and normal_fields:
            instance.save(update_fields=normal_fields)

        return results

    @staticmethod
    def get_video_streams_data(vstreams: list) -> list:
        vstream_data = [{
            "index": vs.get("index"),
            "codec_name": vs.get("codec_name"),
            "width": vs.get("width"),
            "height": vs.get("height"),
            "r_frame_rate": vs.get("r_frame_rate"),
        } for vs in vstreams]
        return vstream_data
    

    @staticmethod
    def get_audio_streams_data(astreams: list) -> list:
        astream_data = [{
            "index": as_.get("index"),
            "codec_name": as_.get("codec_name"),
            "channels": as_.get("channels"),
            "sample_rate": as_.get("sample_rate"),
        } for as_ in astreams]
        return astream_data
    
    @staticmethod
    def upload_packaging_outputs(dir: str, prefix: str, content_type: str=None) -> bool:
        """
        Upload the output files from HLS and DASH packaging to S3
        """
        for fn in os.listdir(dir):
            local_path = os.path.join(dir, fn)
            key = f"{prefix}/{fn}"
            client = StorageClient()
            content_type = content_type or StorageClient.get_mime_type(fn)
            client.upload_file_to_s3(local_path, key, content_type)
        return True
    
    @staticmethod
    def create_and_upload_master_playlist(variant_infos: list, workdir: str, job) -> str:
        """
        Create and upload the HLS master playlist to S3
        """
        master_lines = ["#EXTM3U"]
        for vi in sorted(variant_infos, key=lambda x: x["bandwidth"]):
            master_lines.append(f'#EXT-X-STREAM-INF:BANDWIDTH={vi["bandwidth"]},RESOLUTION={vi["resolution"]}')
            master_lines.append(vi["playlist"].split("/")[-2] + "/" + vi["playlist"].split("/")[-1])
        master_content = "\n".join(master_lines) + "\n"

        master_local = os.path.join(workdir, "master.m3u8")
        with open(master_local, "w", encoding="utf-8") as f:
            f.write(master_content)

        master_key = f"processed/{job.owner.email}/{job.id}/hls/{job.file.id}/master.m3u8"
        client = StorageClient()
        client.upload_file_to_s3(master_local, master_key, "application/vnd.apple.mpegurl")
        return master_key