from .base import BaseEnum


class FilePurposeType(BaseEnum):
    PROFILE_PICTURE = "profile_picture"
    FILM_POSTER = "film_poster"
    TRAILER = "trailer"
    TEASER = "teaser"
    SNIPPET = "snippet"
    MAIN_FILE = "main_file"
    OTHERS = "others"


class JobStatus(BaseEnum):
    PENDING = "pending"
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"


class Stage(BaseEnum):
    CHECKSUM = "checksum"
    PROBE = "probe"
    VALIDATE = "validate"
    TRANSCODE = "transcode"
    PACKAGE_HLS = "package_hls"
    PACKAGE_DASH = "package_dash"
    THUMBNAILS = "thumbnails"
    AUDIO = "audio"
    FINALIZE = "finalize"


# Default renditions: width, height, bitrate in kbps
DEFAULT_RENDITIONS = [
    {"name": "1080p", "width": 1920, "height": 1080, "video_bitrate": 5000, "audio_bitrate": 128},
    {"name": "720p",  "width": 1280, "height": 720,  "video_bitrate": 3000, "audio_bitrate": 128},
    {"name": "480p",  "width": 854,  "height": 480,  "video_bitrate": 1200, "audio_bitrate": 96},
]