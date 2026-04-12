import factory

from core.feed.models import Purchase
from core.feed.tests.factories.feed_factories import FeedFactory
from core.users.tests.factories.user_factories import UserFactory
from core.utils import enums


class PurchaseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Purchase

    owner = factory.SubFactory(UserFactory)
    film = factory.SubFactory(FeedFactory, owner=factory.SelfAttribute("..owner"))
    status = enums.PurchaseStatusType.ACTIVE.value
    payment_status = enums.PurchasePaymentStatus.COMPLETED.value
    method = enums.PaymentType.BANK_CHARGE.value
