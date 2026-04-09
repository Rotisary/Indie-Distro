from django.urls import path

from .views import (
    ListCreateFeed,
    ListCreateShort,
    RetrieveUpdateDeleteFeed,
    PublicFeedList,
    Bookmark,
    RemoveBookmark,
    RetrieveUpdateDeleteShort,
    PublicShortsList,
    PurchaseFilm,
    UserFeedsList,
    UserShortsList,
)

urlpatterns = [
    path("films/", ListCreateFeed.as_view(), name="list-create-film"),
    path("films/all/", PublicFeedList.as_view(), name="public-film-list"),
    path("users/<int:pk>/feeds/", UserFeedsList.as_view(), name="user-film-list"),
    path("films/<int:pk>/", RetrieveUpdateDeleteFeed.as_view(), name="rud-film"),
    path("films/<int:pk>/purchase", PurchaseFilm.as_view(), name="purchase-film"),
    # path("purchases/", ListMyPurchases.as_view(), name="list-my-purchases"),
    path("bookmark/", Bookmark.as_view(), name="bookmark-film"),
    path("remove_bookmark/", RemoveBookmark.as_view(), name="unbookmark-film"),
    path("shorts/", ListCreateShort.as_view(), name="list-create-short"),
    path("shorts/all/", PublicShortsList.as_view(), name="public-short-list"),
    path("users/<int:pk>/shorts/", UserShortsList.as_view(), name="user-short-list"),
    path("shorts/<int:pk>/", RetrieveUpdateDeleteShort.as_view(), name="rud-short"),
]
