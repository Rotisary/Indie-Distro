import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.test import APIClient

from core.feed import views as feed_views
from core.feed.models import Feed, Short
from core.feed.tests.factories.feed_factories import FeedFactory, ShortFactory
from core.file_storage.tests.factories.file_storage_factories import FileModelFactory
from core.utils import enums

pytestmark = pytest.mark.django_db

LIST_CREATE_FILM_URL = reverse("list-create-film")
PUBLIC_FILM_LIST_URL = reverse("public-film-list")
BOOKMARK_URL = reverse("bookmark-film")
REMOVE_BOOKMARK_URL = reverse("unbookmark-film")
LIST_CREATE_SHORT_URL = reverse("list-create-short")
PUBLIC_SHORT_LIST_URL = reverse("public-short-list")


def user_films_url(user_id):
    return reverse("user-film-list", args=[user_id])


def film_detail_url(film_id):
    return reverse("rud-film", args=[film_id])


def purchase_film_url(film_id):
    return reverse("purchase-film", args=[film_id])


def user_shorts_url(user_id):
    return reverse("user-short-list", args=[user_id])


def short_detail_url(short_id):
    return reverse("rud-short", args=[short_id])


def build_film_payload(**overrides):
    payload = {
        "title": "Test Film",
        "plot": "A test plot",
        "genre": [enums.FilmGenreType.ACTION.value],
        "type": enums.FilmCategoryType.STANDALONE.value,
        "cast": ["Actor One"],
        "crew": {"director": "Director"},
        "language": "en",
        "sale_type": enums.FilmSaleType.ONE_TIME_SALE.value,
        "price": "19.99",
    }
    payload.update(overrides)
    return payload


def build_short_payload(film, file_model, **overrides):
    payload = {
        "film": film.id,
        "file": file_model.id,
        "type": enums.ShortType.TRAILER.value,
        "caption": "Test caption",
        "tags": ["tag1", "tag2"],
        "language": "en",
    }
    payload.update(overrides)
    return payload


def build_bookmark_payload(object_id, model_name="Feed"):
    return {"id": str(object_id), "model_name": model_name}


def build_purchase_payload(
    method=enums.PaymentType.BANK_CHARGE.value, wallet_pin="1234"
):
    return {"method": method, "wallet_pin": wallet_pin}


# List/create films

def test_list_create_film_get_success(creator_client, creator_user):
    FeedFactory(owner=creator_user)
    FeedFactory()

    response = creator_client.get(LIST_CREATE_FILM_URL)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["owner"]["id"] == creator_user.id


def test_list_create_film_get_unauthorized(anonymous_client):
    response = anonymous_client.get(LIST_CREATE_FILM_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_create_film_get_forbidden(authenticated_client):
    response = authenticated_client.get(LIST_CREATE_FILM_URL)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_list_create_film_get_empty(creator_client):
    response = creator_client.get(LIST_CREATE_FILM_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data == []


def test_list_create_film_post_success(creator_client):
    payload = build_film_payload()

    response = creator_client.post(LIST_CREATE_FILM_URL, payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert Feed.objects.filter(title=payload["title"]).exists()


def test_list_create_film_post_unauthorized(anonymous_client):
    response = anonymous_client.post(
        LIST_CREATE_FILM_URL, build_film_payload(), format="json"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_create_film_post_forbidden(authenticated_client):
    response = authenticated_client.post(
        LIST_CREATE_FILM_URL, build_film_payload(), format="json"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_list_create_film_post_invalid_payload(creator_client):
    payload = build_film_payload(cast=["a", "b", "c", "d", "e", "f"])

    response = creator_client.post(LIST_CREATE_FILM_URL, payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_list_create_film_post_missing_required_fields(creator_client):
    response = creator_client.post(LIST_CREATE_FILM_URL, {}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_list_create_film_not_found(anonymous_client):
    response = anonymous_client.get("/api/feed/films/unknown/")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# Film detail

def test_film_detail_get_success(authenticated_client, film):
    response = authenticated_client.get(film_detail_url(film.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == film.id


def test_film_detail_get_unauthorized(anonymous_client, film):
    response = anonymous_client.get(film_detail_url(film.id))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_film_detail_get_not_found(authenticated_client):
    response = authenticated_client.get(film_detail_url(999999))

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_film_detail_patch_partial_success(creator_client, film):
    payload = {"title": "Updated Title"}

    response = creator_client.patch(film_detail_url(film.id), payload, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["title"] == payload["title"]


def test_film_detail_patch_full_success(creator_client, film):
    payload = build_film_payload(title="Full Update", plot="Updated plot")

    response = creator_client.patch(film_detail_url(film.id), payload, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["title"] == payload["title"]


def test_film_detail_patch_unauthorized(anonymous_client, film):
    response = anonymous_client.patch(
        film_detail_url(film.id), {"title": "Nope"}, format="json"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_film_detail_patch_forbidden_released(creator_client, creator_user):
    released_film = FeedFactory(owner=creator_user, is_released=True)

    response = creator_client.patch(
        film_detail_url(released_film.id), {"title": "Nope"}, format="json"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_film_detail_patch_invalid_payload(creator_client, film):
    today = timezone.now().date().isoformat()

    response = creator_client.patch(
        film_detail_url(film.id), {"release_date": today}, format="json"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_film_detail_patch_not_found(creator_client):
    response = creator_client.patch(
        film_detail_url(999999), {"title": "Nope"}, format="json"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_film_detail_delete_success(creator_client, film):
    response = creator_client.delete(film_detail_url(film.id))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Feed.objects.filter(id=film.id).exists()


def test_film_detail_delete_unauthorized(anonymous_client, film):
    response = anonymous_client.delete(film_detail_url(film.id))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_film_detail_delete_not_found(creator_client):
    response = creator_client.delete(film_detail_url(999999))

    assert response.status_code == status.HTTP_404_NOT_FOUND


# Public film list

def test_public_film_list_success(anonymous_client):
    released = FeedFactory(is_released=True)
    FeedFactory(is_released=False)

    response = anonymous_client.get(PUBLIC_FILM_LIST_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == released.id


def test_public_film_list_pagination(anonymous_client):
    FeedFactory.create_batch(12, is_released=True)

    response = anonymous_client.get(f"{PUBLIC_FILM_LIST_URL}?limit=5&offset=0")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 12
    assert len(response.data["results"]) == 5


def test_public_film_list_filtering(anonymous_client):
    FeedFactory(is_released=True, type=enums.FilmCategoryType.SERIES.value)
    FeedFactory(is_released=True, type=enums.FilmCategoryType.STANDALONE.value)

    response = anonymous_client.get(
        f"{PUBLIC_FILM_LIST_URL}?type={enums.FilmCategoryType.SERIES.value}"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1


def test_public_film_list_empty(anonymous_client):
    FeedFactory(is_released=False)

    response = anonymous_client.get(PUBLIC_FILM_LIST_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 0
    assert response.data["results"] == []


def test_public_film_list_invalid_filter(anonymous_client):
    response = anonymous_client.get(f"{PUBLIC_FILM_LIST_URL}?type=invalid")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_public_film_list_forbidden(monkeypatch, user):
    monkeypatch.setattr(feed_views.PublicFeedList, "permission_classes", [IsAdminUser])

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(PUBLIC_FILM_LIST_URL)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_public_film_list_not_found(anonymous_client):
    response = anonymous_client.get("/api/feed/films/all/unknown/")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# User film list

def test_user_films_list_success(authenticated_client, creator_user):
    FeedFactory.create_batch(2, owner=creator_user, is_released=True)
    FeedFactory(owner=creator_user, is_released=False)

    response = authenticated_client.get(user_films_url(creator_user.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2


def test_user_films_list_unauthorized(anonymous_client, creator_user):
    response = anonymous_client.get(user_films_url(creator_user.id))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_films_list_forbidden(monkeypatch, user, creator_user):
    monkeypatch.setattr(feed_views.UserFeedsList, "permission_classes", [IsAdminUser])

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(user_films_url(creator_user.id))

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_user_films_list_pagination(authenticated_client, creator_user):
    FeedFactory.create_batch(11, owner=creator_user, is_released=True)

    response = authenticated_client.get(
        f"{user_films_url(creator_user.id)}?limit=4&offset=0"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 11
    assert len(response.data["results"]) == 4


def test_user_films_list_filtering(authenticated_client, creator_user):
    FeedFactory(
        owner=creator_user,
        is_released=True,
        type=enums.FilmCategoryType.SERIES.value,
    )
    FeedFactory(
        owner=creator_user,
        is_released=True,
        type=enums.FilmCategoryType.STANDALONE.value,
    )

    response = authenticated_client.get(
        f"{user_films_url(creator_user.id)}?type={enums.FilmCategoryType.SERIES.value}"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1


def test_user_films_list_empty(authenticated_client, creator_user):
    FeedFactory(owner=creator_user, is_released=False)

    response = authenticated_client.get(user_films_url(creator_user.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 0
    assert response.data["results"] == []


def test_user_films_list_invalid_filter(authenticated_client, creator_user):
    response = authenticated_client.get(
        f"{user_films_url(creator_user.id)}?type=invalid"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_user_films_list_not_found(anonymous_client, creator_user):
    response = anonymous_client.get(f"{user_films_url(creator_user.id)}unknown/")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# Film purchase

def test_purchase_film_success(
    monkeypatch, buyer_client, buyer_wallet, creator_user, creator_wallet
):
    film = FeedFactory(owner=creator_user, is_released=False, price="20.00")

    def fake_charge_bank(self):
        return self.PaymentResponse(status="initiated", data={"ok": True})

    monkeypatch.setattr(
        feed_views.payment.PaymentHelper, "charge_bank", fake_charge_bank
    )

    response = buyer_client.post(
        purchase_film_url(film.id), build_purchase_payload(), format="json"
    )

    assert response.status_code == status.HTTP_202_ACCEPTED


def test_purchase_film_unauthorized(anonymous_client, film):
    response = anonymous_client.post(
        purchase_film_url(film.id), build_purchase_payload(), format="json"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_purchase_film_forbidden_own_film(monkeypatch, creator_client, creator_wallet):
    film = FeedFactory(owner=creator_wallet.owner, is_released=False, price="20.00")

    def fake_charge_bank(self):
        return self.PaymentResponse(status="initiated", data={"ok": True})

    monkeypatch.setattr(
        feed_views.payment.PaymentHelper, "charge_bank", fake_charge_bank
    )

    response = creator_client.post(
        purchase_film_url(film.id), build_purchase_payload(), format="json"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_purchase_film_invalid_payload(
    monkeypatch, buyer_client, buyer_wallet, creator_user, creator_wallet
):
    film = FeedFactory(owner=creator_user, is_released=False, price="20.00")

    def fake_charge_bank(self):
        return self.PaymentResponse(status="initiated", data={"ok": True})

    monkeypatch.setattr(
        feed_views.payment.PaymentHelper, "charge_bank", fake_charge_bank
    )

    response = buyer_client.post(
        purchase_film_url(film.id), build_purchase_payload(wallet_pin="0000"), format="json"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_purchase_film_not_found(creator_client):
    response = creator_client.post(
        purchase_film_url(999999), build_purchase_payload(), format="json"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# Bookmark

def test_bookmark_success(authenticated_client, film, user):
    response = authenticated_client.post(
        BOOKMARK_URL, build_bookmark_payload(film.id, "Feed"), format="json"
    )

    assert response.status_code == status.HTTP_200_OK
    film.refresh_from_db()
    assert user in film.saved.all()


def test_bookmark_unauthorized(anonymous_client, film):
    response = anonymous_client.post(
        BOOKMARK_URL, build_bookmark_payload(film.id, "Feed"), format="json"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_bookmark_forbidden(monkeypatch, user, film):
    monkeypatch.setattr(feed_views.Bookmark, "permission_classes", [IsAdminUser])

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        BOOKMARK_URL, build_bookmark_payload(film.id, "Feed"), format="json"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_bookmark_invalid_payload(authenticated_client):
    response = authenticated_client.post(BOOKMARK_URL, {"model_name": "Feed"}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_bookmark_not_found(authenticated_client):
    response = authenticated_client.post(
        BOOKMARK_URL, build_bookmark_payload(999999, "Feed"), format="json"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_remove_bookmark_success(authenticated_client, film, user):
    film.saved.add(user)

    response = authenticated_client.post(
        REMOVE_BOOKMARK_URL, build_bookmark_payload(film.id, "Feed"), format="json"
    )

    assert response.status_code == status.HTTP_200_OK
    film.refresh_from_db()
    assert user not in film.saved.all()


def test_remove_bookmark_unauthorized(anonymous_client, film):
    response = anonymous_client.post(
        REMOVE_BOOKMARK_URL, build_bookmark_payload(film.id, "Feed"), format="json"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_remove_bookmark_forbidden(monkeypatch, user, film):
    monkeypatch.setattr(feed_views.RemoveBookmark, "permission_classes", [IsAdminUser])

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        REMOVE_BOOKMARK_URL, build_bookmark_payload(film.id, "Feed"), format="json"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_remove_bookmark_invalid_payload(authenticated_client):
    response = authenticated_client.post(REMOVE_BOOKMARK_URL, {"model_name": "Feed"}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_remove_bookmark_not_found(authenticated_client):
    response = authenticated_client.post(
        REMOVE_BOOKMARK_URL, build_bookmark_payload(999999, "Feed"), format="json"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# List/create shorts

def test_list_create_short_get_success(creator_client, creator_user):
    ShortFactory(owner=creator_user)
    ShortFactory()

    response = creator_client.get(LIST_CREATE_SHORT_URL)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["owner"]["id"] == creator_user.id


def test_list_create_short_get_unauthorized(anonymous_client):
    response = anonymous_client.get(LIST_CREATE_SHORT_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_create_short_get_forbidden(authenticated_client):
    response = authenticated_client.get(LIST_CREATE_SHORT_URL)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_list_create_short_get_empty(creator_client):
    response = creator_client.get(LIST_CREATE_SHORT_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data == []


def test_list_create_short_post_success(creator_client, film, file_model):
    payload = build_short_payload(film, file_model)

    response = creator_client.post(LIST_CREATE_SHORT_URL, payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert Short.objects.filter(caption=payload["caption"]).exists()


def test_list_create_short_post_unauthorized(anonymous_client, film, file_model):
    response = anonymous_client.post(
        LIST_CREATE_SHORT_URL, build_short_payload(film, file_model), format="json"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_create_short_post_forbidden(authenticated_client, film, file_model):
    response = authenticated_client.post(
        LIST_CREATE_SHORT_URL, build_short_payload(film, file_model), format="json"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_list_create_short_post_invalid_payload(creator_client, film, user):
    other_file = FileModelFactory(owner=user)

    response = creator_client.post(
        LIST_CREATE_SHORT_URL,
        build_short_payload(film, other_file),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_list_create_short_post_missing_required_fields(creator_client):
    response = creator_client.post(LIST_CREATE_SHORT_URL, {}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_list_create_short_not_found(anonymous_client):
    response = anonymous_client.get("/api/feed/shorts/unknown/")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# Short detail

def test_short_detail_get_success(authenticated_client, short):
    response = authenticated_client.get(short_detail_url(short.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == short.id


def test_short_detail_get_unauthorized(anonymous_client, short):
    response = anonymous_client.get(short_detail_url(short.id))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_short_detail_get_not_found(authenticated_client):
    response = authenticated_client.get(short_detail_url(999999))

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_short_detail_patch_partial_success(creator_client, short):
    payload = {"caption": "Updated caption"}

    response = creator_client.patch(short_detail_url(short.id), payload, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["caption"] == payload["caption"]


def test_short_detail_patch_full_success(creator_client, short):
    payload = build_short_payload(short.film, short.file, caption="Full update")

    response = creator_client.patch(short_detail_url(short.id), payload, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["caption"] == payload["caption"]


def test_short_detail_patch_unauthorized(anonymous_client, short):
    response = anonymous_client.patch(
        short_detail_url(short.id), {"caption": "Nope"}, format="json"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_short_detail_patch_forbidden_non_owner(other_creator_client, short):
    response = other_creator_client.patch(
        short_detail_url(short.id), {"caption": "Nope"}, format="json"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_short_detail_patch_forbidden_released(creator_client, creator_user, film):
    released_short = ShortFactory(
        owner=creator_user,
        film=film,
        file=FileModelFactory(owner=creator_user),
        is_released=True,
    )

    response = creator_client.patch(
        short_detail_url(released_short.id), {"caption": "Nope"}, format="json"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_short_detail_patch_invalid_payload(creator_client, short):
    today = timezone.now().date().isoformat()

    response = creator_client.patch(
        short_detail_url(short.id), {"release_date": today}, format="json"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_short_detail_patch_not_found(creator_client):
    response = creator_client.patch(
        short_detail_url(999999), {"caption": "Nope"}, format="json"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_short_detail_delete_success(creator_client, short):
    response = creator_client.delete(short_detail_url(short.id))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Short.objects.filter(id=short.id).exists()


def test_short_detail_delete_unauthorized(anonymous_client, short):
    response = anonymous_client.delete(short_detail_url(short.id))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_short_detail_delete_forbidden(other_creator_client, short):
    response = other_creator_client.delete(short_detail_url(short.id))

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_short_detail_delete_not_found(creator_client):
    response = creator_client.delete(short_detail_url(999999))

    assert response.status_code == status.HTTP_404_NOT_FOUND


# Public short list

def test_public_short_list_success(anonymous_client):
    released = ShortFactory(is_released=True)
    ShortFactory(is_released=False)

    response = anonymous_client.get(PUBLIC_SHORT_LIST_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == released.id


def test_public_short_list_pagination(anonymous_client):
    ShortFactory.create_batch(12, is_released=True)

    response = anonymous_client.get(f"{PUBLIC_SHORT_LIST_URL}?limit=5&offset=0")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 12
    assert len(response.data["results"]) == 5


def test_public_short_list_filtering(anonymous_client):
    ShortFactory(is_released=True, type=enums.ShortType.TEASER.value)
    ShortFactory(is_released=True, type=enums.ShortType.TRAILER.value)

    response = anonymous_client.get(
        f"{PUBLIC_SHORT_LIST_URL}?type={enums.ShortType.TEASER.value}"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1


def test_public_short_list_empty(anonymous_client):
    ShortFactory(is_released=False)

    response = anonymous_client.get(PUBLIC_SHORT_LIST_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 0
    assert response.data["results"] == []


def test_public_short_list_invalid_filter(anonymous_client):
    response = anonymous_client.get(f"{PUBLIC_SHORT_LIST_URL}?type=invalid")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_public_short_list_forbidden(monkeypatch, user):
    monkeypatch.setattr(feed_views.PublicShortsList, "permission_classes", [IsAdminUser])

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(PUBLIC_SHORT_LIST_URL)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_public_short_list_not_found(anonymous_client):
    response = anonymous_client.get("/api/feed/shorts/all/unknown/")

    assert response.status_code == status.HTTP_404_NOT_FOUND


# User short list

def test_user_shorts_list_success(authenticated_client, creator_user):
    ShortFactory.create_batch(2, owner=creator_user, is_released=True)
    ShortFactory(owner=creator_user, is_released=False)

    response = authenticated_client.get(user_shorts_url(creator_user.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2


def test_user_shorts_list_unauthorized(anonymous_client, creator_user):
    response = anonymous_client.get(user_shorts_url(creator_user.id))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_shorts_list_forbidden(monkeypatch, user, creator_user):
    monkeypatch.setattr(feed_views.UserShortsList, "permission_classes", [IsAdminUser])

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(user_shorts_url(creator_user.id))

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_user_shorts_list_pagination(authenticated_client, creator_user):
    ShortFactory.create_batch(11, owner=creator_user, is_released=True)

    response = authenticated_client.get(
        f"{user_shorts_url(creator_user.id)}?limit=4&offset=0"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 11
    assert len(response.data["results"]) == 4


def test_user_shorts_list_filtering(authenticated_client, creator_user):
    ShortFactory(
        owner=creator_user, is_released=True, type=enums.ShortType.TEASER.value
    )
    ShortFactory(
        owner=creator_user, is_released=True, type=enums.ShortType.TRAILER.value
    )

    response = authenticated_client.get(
        f"{user_shorts_url(creator_user.id)}?type={enums.ShortType.TEASER.value}"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1


def test_user_shorts_list_empty(authenticated_client, creator_user):
    ShortFactory(owner=creator_user, is_released=False)

    response = authenticated_client.get(user_shorts_url(creator_user.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 0
    assert response.data["results"] == []


def test_user_shorts_list_invalid_filter(authenticated_client, creator_user):
    response = authenticated_client.get(
        f"{user_shorts_url(creator_user.id)}?type=invalid"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_user_shorts_list_not_found(anonymous_client, creator_user):
    response = anonymous_client.get(f"{user_shorts_url(creator_user.id)}unknown/")

    assert response.status_code == status.HTTP_404_NOT_FOUND
