from django.urls import path

from .views import (
    ListCreateFeed,
    RetrieveUpdateFeed
)

urlpatterns = [
    path("", ListCreateFeed.as_view(), name="list-create-film"),
    path("<int:pk>/", RetrieveUpdateFeed.as_view(), name="retrieve-update-film")
]