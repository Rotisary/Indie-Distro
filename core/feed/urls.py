from django.urls import path

from .views import (
    ListCreateFeed,
    RetrieveUpdateFeed,
    Bookmark,
    RemoveBookmark
)

urlpatterns = [
    path("", ListCreateFeed.as_view(), name="list-create-film"),
    path("<int:pk>/", RetrieveUpdateFeed.as_view(), name="retrieve-update-film"),
    path("bookmark/", Bookmark.as_view(), name="bookmark-film"),
    path("remove_bookmark/", RemoveBookmark.as_view(), name="unbookmark-film"),
]