from decimal import Decimal

from django.contrib.auth.hashers import check_password, make_password
from django.db import models, transaction
from django.db.models import F
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from rest_framework import status

from core.utils import enums, mixins
from core.utils.exceptions import exceptions
from core.websocket.utils import emit_websocket_event
from core.utils.services import FlutterwaveService


class Wallet(mixins.BaseModelMixin):
    owner = models.OneToOneField(
        to="users.User",
        blank=False,
        null=False,
        related_name="wallet",
        on_delete=models.CASCADE,
        verbose_name=_("Wallet Owner"),
    )
    account_reference = models.CharField(
        primary_key=True,
        max_length=20,
        null=False,
        blank=False,
        unique=True,
        verbose_name=_("Flutterwave Sub-Account Reference"),
    )
    barter_id = models.CharField(
        max_length=15,
        null=False,
        blank=False,
        unique=True,
        verbose_name=_("Flutterwave Barter ID"),
    )
    virtual_account_number = models.CharField(
        max_length=10, blank=True, null=True, verbose_name=_("Virtual Account Number")
    )
    virtual_bank_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name=_("Virtual Bank Name")
    )
    virtual_bank_code = models.CharField(
        max_length=50, blank=True, null=True, verbose_name=_("Virtual Bank Code")
    )
    created_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Flutterwave Sub-Account Creation Date"),
        help_text=_("Date when the Flutterwave sub-account was created"),
    )
    earnings_balance = models.DecimalField(
        default=0, max_digits=15, decimal_places=2, null=False, blank=True
    )
    funding_balance = models.DecimalField(
        default=0, max_digits=15, decimal_places=2, null=False, blank=True
    )
    total_balance = models.DecimalField(
        default=0, max_digits=15, decimal_places=2, null=False, blank=True
    )
    wallet_pin = models.CharField(null=True, blank=True)
    creation_status = models.CharField(
        max_length=20,
        choices=enums.WalletCreationStatus.choices(),
        default=enums.WalletCreationStatus.PENDING.value,
        verbose_name=_("Wallet Creation Status"),
    )

    class Meta:
        verbose_name = _("Wallet")
        verbose_name_plural = _("Wallets")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(funding_balance__gte=0),
                name="funding_balance_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(earnings_balance__gte=0),
                name="earnings_balance_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(total_balance__gte=0),
                name="total_balance_non_negative",
            ),
        ]

    def __str__(self):
        return f"{self.owner.email} wallet <{self.id}>"

    class EventData:
        @staticmethod
        def on_wallet_created(instance: "Wallet") -> dict:
            return {
                "type": enums.WalletEventType.WALLET_CREATED.value,
                "data": {
                    "status": enums.WalletCreationStatus.COMPLETED.value,
                    "wallet_id": instance.pk,
                    "account_reference": instance.account_reference,
                    "barter_id": instance.barter_id,
                    "timestamp": timezone.now().isoformat(),
                },
            }

        @staticmethod
        def on_wallet_failed(instance: "Wallet") -> dict:
            return {
                "type": enums.WalletEventType.WALLET_FAILED.value,
                "data": {
                    "status": enums.WalletCreationStatus.FAILED.value,
                    "wallet_id": instance.pk,
                    "timestamp": timezone.now().isoformat(),
                },
            }

        @staticmethod
        def on_virtual_account_fetched(instance: "Wallet") -> dict:
            return {
                "type": enums.WalletEventType.VIRTUAL_ACCOUNT_FETCHED.value,
                "data": {
                    "status": "fetched",
                    "wallet_id": instance.pk,
                    "virtual_account": {
                        "virtual_bank_name": instance.virtual_bank_name,
                        "virtual_bank_code": instance.virtual_bank_code,
                        "virtual_account_number": instance.virtual_account_number,
                    },
                    "timestamp": timezone.now().isoformat(),
                },
            }

        @staticmethod
        def on_virtual_account_failed(instance: "Wallet") -> dict:
            return {
                "type": enums.WalletEventType.VIRTUAL_ACCOUNT_FAILED.value,
                "data": {
                    "status": "failed",
                    "wallet_id": instance.pk,
                    "timestamp": timezone.now().isoformat(),
                },
            }

    def emit_event(self, event_type: str):
        emit_websocket_event(self, event_type)

    def has_pin(self):
        return bool(self.wallet_pin)

    def set_pin(self, pin: str):
        if not pin:
            raise exceptions.WalletException(["Invalid PIN"], "PIN cannot be empty")
        self.wallet_pin = make_password(pin)
        self.save(update_fields=["wallet_pin"])

    def verify_pin(self, pin: str) -> bool:
        if not self.wallet_pin:
            raise exceptions.WalletException(
                ["PIN Not Set"], "Wallet PIN has not been set yet"
            )
        if not pin:
            raise exceptions.WalletException(["Invalid PIN"], "PIN cannot be empty")

        if "$" in self.wallet_pin:
            if check_password(pin, self.wallet_pin):
                return True
            raise exceptions.WalletException(
                ["Invalid PIN"], "The PIN you provided is incorrect"
            )

        if self.wallet_pin == pin:
            self.set_pin(pin)
            return True

        raise exceptions.WalletException(
            ["Invalid PIN"], "The PIN you provided is incorrect"
        )

    def verify_flutterwave_balance(self, amount, *, currency: str = "NGN"):
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))

        if amount <= 0:
            raise exceptions.WalletException(
                ["Invalid Number"], "Must be greater than zero"
            )

        service = FlutterwaveService()
        balance_data = service.check_payout_subaccount_balance(
            self.account_reference, currency=currency
        )
        provider_balance = balance_data.get("balance")
        wallet_balance = self.total_balance

        if provider_balance != wallet_balance:
            raise exceptions.CustomException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="Flutterwave balance does not match wallet balance.",
                errors={
                    "flutterwave_balance": str(provider_balance),
                    "wallet_balance": str(wallet_balance),
                },
            )

        if provider_balance < amount:
            raise exceptions.CustomException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="Flutterwave balance is insufficient for this transfer.",
                errors={
                    "flutterwave_balance": str(provider_balance),
                    "requested_amount": str(amount),
                },
            )

        return True

    def withdraw_funds(self, amount, is_earnings=False):
        if is_earnings:
            self.withdraw_from_earnings(amount)
        else:
            self.pay_with_wallet(amount)

    def pay_to_wallet(self, amount, is_funding=False):
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))

        if amount <= 0:
            raise exceptions.WalletException(
                ["Invalid Number"], "Must be greater than zero"
            )

        with transaction.atomic():
            locked_wallet = Wallet.objects.select_for_update().get(pk=self.pk)

            if is_funding:
                locked_wallet.funding_balance = F("funding_balance") + amount
            else:
                locked_wallet.earnings_balance = F("earnings_balance") + amount
            locked_wallet.total_balance = F("total_balance") + amount
            locked_wallet.save(
                update_fields=["funding_balance", "earnings_balance", "total_balance"]
            )

        self.refresh_from_db(
            fields=["funding_balance", "earnings_balance", "total_balance"]
        )

    def pay_with_wallet(self, amount):
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))

        if amount <= 0:
            raise exceptions.WalletException(
                ["Invalid Number"], "Must be greater than zero"
            )

        with transaction.atomic():
            locked_wallet = Wallet.objects.select_for_update().get(pk=self.pk)

            if locked_wallet.funding_balance < amount:
                raise exceptions.WalletException(
                    ["Insufficient funds"],
                    "Insufficient funds in wallet, fund your wallet to continue",
                )

            locked_wallet.funding_balance = F("funding_balance") - amount
            locked_wallet.total_balance = F("total_balance") - amount
            locked_wallet.save(update_fields=["funding_balance", "total_balance"])

        self.refresh_from_db(fields=["funding_balance", "total_balance"])

    def withdraw_from_earnings(self, amount):
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))

        if amount <= 0:
            raise exceptions.WalletException(
                ["Invalid Number"], "Must be greater than zero"
            )

        with transaction.atomic():
            locked_wallet = Wallet.objects.select_for_update().get(pk=self.pk)

            if locked_wallet.earnings_balance < amount:
                raise exceptions.WalletException(
                    ["Insufficient funds"],
                    "Insufficient funds in wallet, fund your wallet to continue",
                )

            locked_wallet.earnings_balance = F("earnings_balance") - amount
            locked_wallet.total_balance = F("total_balance") - amount
            locked_wallet.save(update_fields=["earnings_balance", "total_balance"])

        self.refresh_from_db(fields=["earnings_balance", "total_balance"])
