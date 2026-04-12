import datetime
from decimal import Decimal

from django.utils import timezone

import factory

from core.feed.models import Feed, Short
from core.file_storage.tests.factories.file_storage_factories import FileModelFactory
from core.users.tests.factories.user_factories import UserFactory
from core.utils import enums


class FeedFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Feed

    owner = factory.SubFactory(
        UserFactory, is_creator=True, account_type=enums.UserAccountType.USER.value
    )
    title = factory.Sequence(lambda n: f"Film {n}")
    plot = "Test plot"
    genre = factory.LazyFunction(lambda: [enums.FilmGenreType.ACTION.value])
    type = enums.FilmCategoryType.STANDALONE.value
    cast = factory.LazyFunction(lambda: ["Actor One"])
    crew = factory.LazyFunction(lambda: {"director": "Director"})
    language = "en"
    sale_type = enums.FilmSaleType.ONE_TIME_SALE.value
    price = Decimal("19.99")
    release_date = factory.LazyFunction(
        lambda: timezone.now().date() + datetime.timedelta(days=30)
    )
    is_released = False


class ShortFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Short

    owner = factory.SubFactory(
        UserFactory, is_creator=True, account_type=enums.UserAccountType.USER.value
    )
    film = factory.SubFactory(FeedFactory, owner=factory.SelfAttribute("..owner"))
    file = factory.SubFactory(FileModelFactory, owner=factory.SelfAttribute("..owner"))
    type = enums.ShortType.TRAILER.value
    caption = "Test caption"
    tags = factory.LazyFunction(lambda: ["tag1", "tag2"])
    release_date = factory.LazyFunction(
        lambda: timezone.now().date() + datetime.timedelta(days=7)
    )
    is_released = False
