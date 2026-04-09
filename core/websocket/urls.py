from django.urls import path

from .views import EventReplayView

urlpatterns = [
    path("events/last/", EventReplayView.as_view(), name="websocket-event-replay"),
]
