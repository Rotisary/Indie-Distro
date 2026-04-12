from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from core.feed.tests.factories.feed_factories import FeedFactory, ShortFactory
from core.feed.tests.factories.purchase_factories import PurchaseFactory
from core.file_storage.tests.factories.file_storage_factories import FileModelFactory
from core.users.tests.factories.user_factories import UserFactory
from core.utils import enums
from core.wallet.tests.factories.wallet_factories import WalletFactory


@pytest.fixture
def anonymous_client():
    return APIClient()


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def authenticated_client(user):
    client = APIClient()
    token = user.retrieve_auth_token()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token['access']}")
    return client


@pytest.fixture
def admin_user():
    return UserFactory(
        is_staff=True,
        is_superuser=True,
        account_type=enums.UserAccountType.SUPER_ADMINISTRATOR.value,
    )


@pytest.fixture
def admin_client(admin_user):
    client = APIClient()
    token = admin_user.retrieve_auth_token()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token['access']}")
    return client


@pytest.fixture
def creator_user():
    return UserFactory(is_creator=True, account_type=enums.UserAccountType.USER.value)


@pytest.fixture
def creator_client(creator_user):
    client = APIClient()
    token = creator_user.retrieve_auth_token()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token['access']}")
    return client


@pytest.fixture
def creator_wallet(creator_user):
    return WalletFactory(
        owner=creator_user,
        wallet_pin="1234",
        funding_balance=Decimal("500.00"),
        total_balance=Decimal("500.00"),
    )


@pytest.fixture
def other_creator_user():
    return UserFactory(is_creator=True, account_type=enums.UserAccountType.USER.value)


@pytest.fixture
def other_creator_client(other_creator_user):
    client = APIClient()
    token = other_creator_user.retrieve_auth_token()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token['access']}")
    return client


@pytest.fixture
def buyer_user():
    return UserFactory(is_creator=False, account_type=enums.UserAccountType.USER.value)


@pytest.fixture
def buyer_client(buyer_user):
    client = APIClient()
    token = buyer_user.retrieve_auth_token()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token['access']}")
    return client


@pytest.fixture
def buyer_wallet(buyer_user):
    return WalletFactory(
        owner=buyer_user,
        wallet_pin="1234",
        funding_balance=Decimal("500.00"),
        total_balance=Decimal("500.00"),
    )


@pytest.fixture
def film(creator_user):
    return FeedFactory(owner=creator_user, is_released=False)


@pytest.fixture
def released_film(creator_user):
    return FeedFactory(owner=creator_user, is_released=True)


@pytest.fixture
def file_model(creator_user):
    return FileModelFactory(owner=creator_user)


@pytest.fixture
def short(creator_user, film, file_model):
    return ShortFactory(
        owner=creator_user, film=film, file=file_model, is_released=False
    )


@pytest.fixture
def released_short(creator_user, film):
    return ShortFactory(
        owner=creator_user,
        film=film,
        file=FileModelFactory(owner=creator_user),
        is_released=True,
    )


@pytest.fixture
def server_auth_headers(settings):
    header_name = f"HTTP_{settings.SERVER_SECRET_KEY_FIELD_NAME}"
    return {header_name: settings.SERVER_SECRET_KEY}


@pytest.fixture
def stream_playback_settings(settings):
    settings.STREAM_COOKIE_SECRET = "test-stream-secret"
    settings.STREAM_BASE_URL = "https://stream.example.com"
    settings.STREAM_COOKIE_NAME = "stream_auth"
    settings.STREAM_COOKIE_TTL_SECONDS = 900
    settings.STREAM_COOKIE_SECURE = False
    settings.STREAM_COOKIE_SAMESITE = "Lax"
    return settings


@pytest.fixture
def released_film_with_playback(released_film, creator_user):
    FileModelFactory(
        owner=creator_user,
        film=released_film,
        hls_master_key="media/films/master.m3u8",
    )
    return released_film


@pytest.fixture
def active_purchase(buyer_user, released_film_with_playback):
    return PurchaseFactory(owner=buyer_user, film=released_film_with_playback)


@pytest.fixture
def released_short_with_playback(creator_user, film):
    file_model = FileModelFactory(
        owner=creator_user,
        hls_master_key="media/shorts/master.m3u8",
    )
    return ShortFactory(
        owner=creator_user,
        film=film,
        file=file_model,
        is_released=True,
    )
