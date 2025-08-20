from django.urls import path

from .views import (
    ListCreateFeed,
)

urlpatterns = [
    path("", ListCreateFeed.as_view(), name="list-create-film"),
]