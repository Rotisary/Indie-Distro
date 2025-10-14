import os
import shutil

from celery import shared_task, chain, group, chord
from loguru import logger

from datetime import timedelta
from rest_framework import status

from core.utils.helpers.file_storage import StorageClient, StorageUtils, FileProcessingUtils
from core.file_storage.models import FileProcessingJob, FileModel
from core.utils.enums import JobStatus, Stage, DEFAULT_RENDITIONS, WebhookEvent
from core.utils.exceptions import exceptions
from core.utils.helpers.webhook import WebhookUtils

def resolve_renditions(user_renditions: list[dict] | None) -> list[dict]:
    return user_renditions or DEFAULT_RENDITIONS



@shared_task(bind=True, max_retries=2, default_retry_delay=30, name="file_pipeline.probe", queue="io")
def ffprobe_metadata(self, job_id: int):
    job = FileProcessingJob.objects.get(pk=job_id)
    if job.metadata and job.metadata.get("ffprobe"):
        return job_id

    job.mark_stage(Stage.PROBE.value)
    StorageUtils.ensure_binary_on_path("ffprobe")
    client = StorageClient()
    job_dir = StorageUtils.get_job_workdir(job_id)
    src_dir = StorageUtils.ensure_dir(os.path.join(job_dir, "source"))
    local_src = os.path.join(src_dir, "source_file.mp4")

    # Ensure local source exists (download once)
    if not os.path.exists(local_src):
        client.download_file_from_s3(job.source_key, local_src)

    ffprobe_json = FileProcessingUtils.ffprobe_get_json(local_src)
    job.metadata = {"ffprobe": ffprobe_json}
    FileProcessingUtils.update_obj_fields(
        job, {"metadata": {"ffprobe": ffprobe_json}}
    )
    return job_id


@shared_task(bind=True, name="file_pipeline.validate_metadata", queue="io")
def validate_and_extract_metadata(self, job_id: int):
    job = FileProcessingJob.objects.get(pk=job_id)
    if job.metadata and job.metadata.get("extracted"):
        return job_id
    
    job.mark_stage(Stage.VALIDATE.value)
    data = job.metadata.get("ffprobe")
    fmt = data.get("format")
    streams = data.get("streams")

    if not streams:
        job.mark_failed("No streams in media")
        logger.error("No streams found")
        raise exceptions.CustomException(
            "No streams in media", status.HTTP_400_BAD_REQUEST
        )

    vstreams = [s for s in streams if s.get("codec_type") == "video"]
    astreams = [s for s in streams if s.get("codec_type") == "audio"]
    if not vstreams:
        job.mark_failed("No video stream present")
        logger.error("No video streams found")
        raise exceptions.CustomException(
            "No video stream present", status.HTTP_400_BAD_REQUEST
        )

    duration = float(fmt.get("duration", 0) or vstreams[0].get("duration", 0) or 0)
    size = int(fmt.get("size", 0) or 0)
    if duration <= 0 or size <= 0:
        job.mark_failed("Invalid duration or size")
        logger.error("Invalid duration or size - they cannot be lesser than zero")
        raise exceptions.CustomException(
            "Invalid duration or size", status.HTTP_400_BAD_REQUEST
        )

    extracted = {
        "duration": duration,
        "size": size,
        "format_name": (fmt.get("format_name") or "").split(",")[0],
        "has_audio": bool(astreams),
        "video_streams": FileProcessingUtils.get_video_streams_data(vstreams),
        "audio_streams": FileProcessingUtils.get_audio_streams_data(astreams)
    }
    film = job.file.film
    short = job.file.short
    if film:
        FileProcessingUtils.update_obj_fields(
            film, {"length": timedelta(duration)}
        )
    if short:
        FileProcessingUtils.update_obj_fields(
            short, {"length": timedelta(duration)}
        )
        
    # update job fields
    meta = job.metadata or {}
    meta["extracted"] = extracted
    job.metadata = meta
    FileProcessingUtils.update_obj_fields(
        job, {"metadata": meta}
    )

    # update file fields
    FileProcessingUtils.update_obj_fields(                                                                                                                                                                                                               
        job.file, 
        {
            "file_width": extracted["video_streams"][0].get("width"),
            "file_height": extracted["video_streams"][0].get("height"),
            "file_size": extracted["size"],
            "format_name": extracted["format_name"],
            "last_error": job.error,          
            "has_audio": extracted["has_audio"],
            "last_processed_at": job.date_last_modified
        }
    )
    return job_id


@shared_task(bind=True, time_limit=60*60*4, name="file_pipeline.transcode.rendition", queue="transcoding")
def transcode_rendition(
    self, 
    job_id: int, 
    name: str, 
    width: int, 
    height: int, 
    v_bitrate_k: int, 
    a_bitrate_k: int
):
    """
    Produce an MP4 rendition for the given resolution/bitrate.
    """
    job = FileProcessingJob.objects.get(pk=job_id)
    job.mark_stage(Stage.TRANSCODE.value, {"rendition": name})

    StorageUtils.ensure_binary_on_path("ffmpeg")

    existing = job.renditions or []
    if existing:
        for r in existing:
            if r.get("name") == name:
                return {"name": r.get("name"), "mp4_key": r.get("mp4_key")} 

    client = StorageClient()
    job_dir = StorageUtils.get_job_workdir(job_id)
    src_dir = StorageUtils.ensure_dir(os.path.join(job_dir, "source"))
    mp4_dir = StorageUtils.ensure_dir(os.path.join(job_dir, "mp4"))
    local_src = os.path.join(src_dir, "source_file.mp4")

    # Ensure local source exists (download once)
    if not os.path.exists(local_src):
        client.download_file_from_s3(job.source_key, local_src)
    local_out = os.path.join(mp4_dir, f"{name}.mp4")
    
    # Baseline H.264 + AAC MP4
    vf = (
        f"scale=w={width}:h={height}:force_original_aspect_ratio=decrease:force_divisible_by=2,"
        f"pad=w={width}:h={height}:x=(ow-iw)/2:y=(oh-ih)/2:color=black,"
        "setsar=1,setdar=16/9"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", local_src,
        "-vf", vf,
        "-c:v", "libx264", "-profile:v", "main", "-preset", "veryfast",
        "-b:v", f"{v_bitrate_k}k", "-maxrate", f"{int(v_bitrate_k*1.2)}k", "-bufsize", f"{int(v_bitrate_k*2)}k",
        "-c:a", "aac", "-b:a", f"{a_bitrate_k}k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-g", "60",
        "-keyint_min", "60",
        "-sc_threshold", "0",
        local_out,
    ]
    StorageUtils.run_cmd(cmd, timeout=60*60*4)

    # Upload processed file to s3
    out_key = f"processed/{job.owner.email}/{job.id}/mp4/{job.file.id}/{name}.mp4"
    client.upload_file_to_s3(local_out, out_key, content_type="video/mp4")
    
    renditions = job.renditions or []
    renditions = [r for r in renditions if r.get("name") != name]
    renditions.append({
        "name": name, 
        "mp4_key": out_key, 
        "width": width, 
        "height": height, 
        "video_bitrate": v_bitrate_k, 
        "audio_bitrate": a_bitrate_k
    })
    FileProcessingUtils.update_obj_fields(
        job, {"renditions": renditions}
    )
    return {"name": name, "mp4_key": out_key}


@shared_task(bind=True, time_limit=60*60*2, name="file_pipeline.package.hls", queue="packaging")
def package_hls(self, job_id: int):
    """
    Use ffmpeg to package HLS variants and a master playlist from produced MP4 renditions.
    """
    job = FileProcessingJob.objects.get(pk=job_id)
    job.mark_stage(Stage.PACKAGE_HLS.value)

    StorageUtils.ensure_binary_on_path("ffmpeg")

    existing = (job.packaging or {}).get("hls") or {}
    if existing.get("master"):
        return {"hls_master": existing["master"]}

    renditions = job.renditions or []
    if not renditions:
        job.mark_failed("No renditions to package for HLS")
        logger.error("No renditions to package")
        raise exceptions.CustomException("No renditions", status.HTTP_400_BAD_REQUEST)

    job_dir = StorageUtils.get_job_workdir(job_id)
    mp4_dir = StorageUtils.ensure_dir(os.path.join(job_dir, "mp4"))
    hls_dir = StorageUtils.ensure_dir(os.path.join(job_dir, "hls"))
    client = StorageClient()

    # For each rendition, repackage to HLS (segment)
    variant_infos = []  
    for r in renditions:
        name = r["name"]
        local_mp4 = os.path.join(mp4_dir, f"{name}.mp4")

        # Ensure local source exists (download once)
        if not os.path.exists(local_mp4):
            client.download_file_from_s3(r["mp4_key"], local_mp4)

        variant_dir = StorageUtils.ensure_dir(os.path.join(hls_dir, f"hls_{name}"))
        variant_m3u8 = os.path.join(variant_dir, f"{name}.m3u8")

        cmd = [
            "ffmpeg", "-y",
            "-i", local_mp4,
            "-c", "copy",
            "-f", "hls",
            "-hls_time", "6",
            "-hls_playlist_type", "vod",
            "-hls_segment_filename", os.path.join(variant_dir, f"{name}_%04d.ts"),
            variant_m3u8,
        ]
        StorageUtils.run_cmd(cmd, timeout=60*60)

        # Upload variant playlist + segments
        prefix = f"processed/{job.owner.email}/{job.id}/hls/{job.file.id}/{name}"
        FileProcessingUtils.upload_packaging_outputs(variant_dir, prefix)

        variant_infos.append({
            "name": name,
            "playlist": f"{prefix}/{name}.m3u8",
            "bandwidth": r.get("video_bitrate", 1000)*1000,
            "resolution": f"{r.get('width')}x{r.get('height')}",
        })

    master_key = FileProcessingUtils.create_and_upload_master_playlist(variant_infos, hls_dir, job)

    packaging = job.packaging or {}
    packaging["hls"] = {"master": master_key, "variants": variant_infos}
    FileProcessingUtils.update_obj_fields(job, {"packaging": packaging})
    return {"hls_master": master_key}


@shared_task(bind=True, time_limit=60*60*2, name="file_pipeline.package.dash", queue="packaging")
def package_dash(self, job_id: int):
    """
    Use ffmpeg to package MPEG-DASH (.mpd).
    """
    job = FileProcessingJob.objects.get(pk=job_id)
    job.mark_stage(Stage.PACKAGE_DASH.value)

    StorageUtils.ensure_binary_on_path("ffmpeg")
    existing = (job.packaging or {}).get("dash") or {}
    if existing.get("mpd"):
        return {"dash_mpd": existing["mpd"]}

    renditions = job.renditions or []
    if not renditions:
        job.mark_failed("No renditions to package for DASH")
        logger.error("No renditions to package")
        raise exceptions.CustomException("No renditions", status.HTTP_400_BAD_REQUEST)

    client = StorageClient()
    job_dir = StorageUtils.get_job_workdir(job_id)
    mp4_dir = StorageUtils.ensure_dir(os.path.join(job_dir, "mp4"))
    dash_dir = StorageUtils.ensure_dir(os.path.join(job_dir, "dash"))

    local_inputs = []
    for r in renditions:
        name = r["name"]
        local_mp4 = os.path.join(mp4_dir, f"{name}.mp4")
        if not os.path.exists(local_mp4):
            client.download_file_from_s3(r["mp4_key"], local_mp4)
        local_inputs.append(local_mp4)

    local_mpd = "stream.mpd"
    # Build ffmpeg DASH packaging command
    cmd = ["ffmpeg", "-y"]
    for input in local_inputs:
        cmd += ["-i", input]

    for idx, _ in enumerate(local_inputs):
        cmd += ["-map", f"{idx}:v:0"]
        cmd += ["-map", f"{idx}:a:0?"]

    cmd += [
        "-c", "copy",
        "-f", "dash",
        "-use_timeline", "1",
        "-use_template", "1",
        "-seg_duration", "6",
        "-init_seg_name", "init_$RepresentationID$.m4s",
        "-media_seg_name", "chunk_$RepresentationID$_$Number%05d$.m4s",
        "-adaptation_sets", "id=0,streams=v id=1,streams=a",
        local_mpd,
    ]
    StorageUtils.run_cmd(cmd, timeout=60*60, cwd=dash_dir)

    # Upload all DASH outputs
    prefix = f"processed/{job.owner.email}/{job.id}/dash/{job.file.id}"
    FileProcessingUtils.upload_packaging_outputs(dash_dir, prefix)

    packaging = job.packaging or {}
    packaging["dash"] = {"mpd": f"{prefix}/stream.mpd"}
    FileProcessingUtils.update_obj_fields(job, {"packaging": packaging})
    return {"dash_mpd": f"{prefix}/stream.mpd"}


@shared_task(bind=True, time_limit=30*60, name="file_pipeline.thumbnails", queue="io")
def generate_thumbnails(self, job_id: int):
    """
    Generate thumbnails at fixed intervals from top rendition.
    """
    job = FileProcessingJob.objects.get(pk=job_id)
    job.mark_stage(Stage.THUMBNAILS.value)

    StorageUtils.ensure_binary_on_path("ffmpeg")
    existing = job.thumbnails or []
    if existing:
        return {"thumbnails": existing}

    renditions = job.renditions or []
    if not renditions:
        job.mark_failed("No renditions to generate thumbnails from")
        logger.error("No renditions to generate thumbnails from")
        raise exceptions.CustomException("No renditions", status.HTTP_400_BAD_REQUEST)

    top_rend = sorted(renditions, key=lambda r: r["video_bitrate"], reverse=True)[0]
    name = top_rend["name"]
    client = StorageClient()
    job_dir = StorageUtils.get_job_workdir(job_id)
    mp4_dir = StorageUtils.ensure_dir(os.path.join(job_dir, "mp4"))
    thumbnail_dir = StorageUtils.ensure_dir(os.path.join(job_dir, "thumbnail"))

    top_rend_mp4 = os.path.join(mp4_dir, f"{name}.mp4")
    if not os.path.exists(top_rend_mp4):
        client.download_file_from_s3(top_rend["mp4_key"],  top_rend_mp4)
    
    local_thumb_dir = StorageUtils.ensure_dir(os.path.join(thumbnail_dir, "thumbs"))

    # Extract 1 frame every 10 seconds, 5 thumbnails max
    cmd = [
        "ffmpeg", "-y",
        "-i", top_rend_mp4,
        "-vf", "fps=1/10,scale=640:-1",
        "-frames:v", "5",
        os.path.join(local_thumb_dir, "thumb_%03d.jpg"),
    ]
    StorageUtils.run_cmd(cmd, timeout=30*60)

    uploaded = []
    # upload generated thumbnail files to s3 and save their keys to a list
    prefix = f"processed/{job.owner.email}/{job.id}/thumbnails/{job.file.id}"
    for fn in sorted(os.listdir(local_thumb_dir)):
        local_path = os.path.join(local_thumb_dir, fn)
        key = f"{prefix}/{fn}"
        client.upload_file_to_s3(local_path, key, "image/jpeg")
        uploaded.append(key)

    FileProcessingUtils.update_obj_fields(job, {"thumbnails": uploaded})
    return {"thumbnails": uploaded}


@shared_task(bind=True, name="file_pipeline.finalize", queue="io")
def finalize_job(self, job_id: int):
    job = FileProcessingJob.objects.get(pk=job_id)
    job.mark_completed()

    # create webhook payload and trigger webhooks
    payload = {
        "status": JobStatus.COMPLETED.value,
        "owner": job.owner.id,
        "file": {
            "file_id": job.file.id,
            "file_name": job.file.original_filename,
            "file_purpose": job.file.file_purpose,
            "file_key": job.file.file_key,
        },
        "media": {
            "media_obj_id": job.file.film.id if job.file.film else (job.file.short.id if job.file.short else None),
            "media_type": "film" if job.file.film else "short",
        }
    }
    WebhookUtils.trigger_webhooks(WebhookEvent.PROCESSING_COMPLETED.value, payload, owner_id=job.owner.id)
    StorageUtils.cleanup_job_workdir(job_id)
    logger.success(f"Processing job {job_id} completed")
    return job_id


@shared_task(bind=True, max_retries=3, default_retry_delay=30, name="file_pipeline.start", queue="beats")
def start_pipeline(self, job_id: int, renditions: list[dict] | None = None):
    """
    Entry: build the chain and kick it off. Keep the chain orchestration in one place.
    """
    renditions = resolve_renditions(renditions)

    # Build transcode subtasks (one per rendition) — run in parallel with group
    transcode_group = group(
        transcode_rendition.si(
            job_id, 
            r["name"], 
            r["width"], 
            r["height"], 
            r["video_bitrate"], 
            r["audio_bitrate"])
        for r in renditions
    )

    packaging_group = group(
        package_hls.si(job_id),
        package_dash.si(job_id),
    )

    flow = chain(
        ffprobe_metadata.si(job_id),
        validate_and_extract_metadata.si(job_id),
        transcode_group,
        packaging_group,
        generate_thumbnails.si(job_id),
        finalize_job.si(job_id),
    )
    flow.apply_async()
    return {"status": "enqueued", "job_id": job_id, "renditions": [r["name"] for r in renditions]}