from django.urls import path
from .views import RetrievePlaybackURL, RefreshPlaybackCookie



urlpatterns = [
    path("get_url/", RetrievePlaybackURL.as_view(), name="retrieve-playback-url"),
    path("token/refresh/", RefreshPlaybackCookie.as_view(), name="refresh-playback-cookie")
]