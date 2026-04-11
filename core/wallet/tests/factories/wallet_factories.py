from decimal import Decimal

import factory

from core.users.tests.factories.user_factories import UserFactory
from core.utils import enums
from core.wallet.models import Wallet


class WalletFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Wallet

    owner = factory.SubFactory(
        UserFactory, is_creator=True, account_type=enums.UserAccountType.USER.value
    )
    account_reference = factory.Sequence(lambda n: f"acct-{n:05d}")
    barter_id = factory.Sequence(lambda n: f"barter-{n:04d}")
    wallet_pin = "1234"
    funding_balance = Decimal("0.00")
    total_balance = Decimal("0.00")
    earnings_balance = Decimal("0.00")
    creation_status = enums.WalletCreationStatus.COMPLETED.value
