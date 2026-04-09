from django.urls import path
from .views import (
    RetrieveFilmPlaybackURL,
    RefreshFilmPlaybackCookie,
    RetrieveShortPlaybackURL,
    RefreshShortPlaybackCookie,
)

urlpatterns = [
    path(
        "films/get_url/",
        RetrieveFilmPlaybackURL.as_view(),
        name="retrieve-film-playback-url",
    ),
    path(
        "films/token/refresh/",
        RefreshFilmPlaybackCookie.as_view(),
        name="refresh-film-playback-cookie",
    ),
    path(
        "shorts/get_url/",
        RetrieveShortPlaybackURL.as_view(),
        name="retrieve-short-playback-url",
    ),
    path(
        "shorts/token/refresh/",
        RefreshShortPlaybackCookie.as_view(),
        name="refresh-short-playback-cookie",
    ),
]
