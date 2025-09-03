from django.urls import path
from .views import RetrievePlaybackURL, RefreshPlaybackToken



urlpatterns = [
    path("get_url/", RetrievePlaybackURL.as_view(), name="retrieve-playback-url"),
    path("token/refresh/", RefreshPlaybackToken.as_view(), name="refresh-playback-token")
]