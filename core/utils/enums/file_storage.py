from .base import BaseEnum


class FilePurposeType(BaseEnum):
    PROFILE_PICTURE = "profile_picture"
    FILM_POSTER = "film_poster"
    TRAILER = "trailer"
    TEASER = "teaser"
    SNIPPET = "snippet"
    MAIN_FILE = "main_file"
    OTHERS = "others"