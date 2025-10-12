from django.urls import path

from .views import (
    ListCreateFeed,
    ListCreateShort,
    RetrieveUpdateDeleteFeed,
    Bookmark,
    RemoveBookmark,
    RetrieveUpdateDeleteShort
)

urlpatterns = [
    path("films/", ListCreateFeed.as_view(), name="list-create-film"),
    path("films/<int:pk>/", RetrieveUpdateDeleteFeed.as_view(), name="rud-film"),
    path("bookmark/", Bookmark.as_view(), name="bookmark-film"),
    path("remove_bookmark/", RemoveBookmark.as_view(), name="unbookmark-film"),
    path("shorts/", ListCreateShort.as_view(), name="list-create-short"),
    path("shorts/<int:pk>/", RetrieveUpdateDeleteShort.as_view(), name="rud-short"),
]