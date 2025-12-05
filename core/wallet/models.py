from django.db import models, transaction
from django.db.models import F
from django.utils.translation import gettext_lazy as _

from core.utils import mixins
from core.utils import enums
from core.utils.commons.utils.parsers import Parsers
from core.utils.exceptions import exceptions


class Wallet(mixins.BaseModelMixin):
    owner = models.OneToOneField(
        to = "users.User",
        blank = False,
        null = False,
        related_name = 'wallet',
        on_delete = models.CASCADE,
        verbose_name = _("Wallet Owner")
    )
    account_reference = models.CharField(
        primary_key=True,
        max_length=20,
        null=False, 
        blank=False,
        unique=True,
        verbose_name=_("Flutterwave Sub-Account Reference")
    )
    barter_id = models.CharField(
        max_length=15,
        null=False,
        blank=False,
        unique=True,
        verbose_name=_("Flutterwave Barter ID")
    )
    virtual_account_number = models.CharField(
        max_length=10, 
        blank=True, 
        null=True, 
        verbose_name=_("Virtual Account Number")
    )
    virtual_bank_name = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name=_("Virtual Bank Name")
    )
    virtual_bank_code = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name=_("Virtual Bank Code")
    )
    created_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Flutterwave Sub-Account Creation Date"),
        help_text=_("Date when the Flutterwave sub-account was created")
    )
    earnings_balance = models.DecimalField(
        default=0,
        max_digits=15,
        decimal_places=2,
        null=False,
        blank=True
    )
    funding_balance = models.DecimalField(
        default=0,
        max_digits=15,
        decimal_places=2,
        null=False,
        blank=True
    )
    total_balance = models.DecimalField(
        default=0,
        max_digits=15,
        decimal_places=2,
        null=False,
        blank=True
    )
    wallet_pin = models.CharField(null=True, blank=True)
    creation_status = models.CharField(
        max_length=20,
        choices=enums.WalletCreationStatus.choices(),
        default=enums.WalletCreationStatus.PENDING.value,
        verbose_name=_("Wallet Creation Status")
    )

    class Meta:
        verbose_name = _("Wallet")
        verbose_name_plural = _("Wallets")


    def __str__(self):
        return f"{self.owner.email} wallet <{self.id}>"
    
    def withdraw_funds(self, amount, is_earnings=False):
        if is_earnings:
            self.withdraw_from_earnings(amount)
        else:
            self.pay_with_wallet(amount)
        


    def pay_to_wallet(self, amount, is_funding=False):
        amount = Parsers.parse_float(amount)

        if amount < 0:
            raise exceptions.WalletException(
                ["Invalid Number"], "Must be greater than zero"
            )
        if is_funding:         
            self.funding_balance = F("funding_balance") + amount
        else:
            self.earnings_balance = F("earnings_balance") + amount
        self.total_balance = F("total_balance") + amount
        self.save()
        self.refresh_from_db(fields=[
            "funding_balance", "earnings_balance", "total_balance"
        ])

    def pay_with_wallet(self, amount):
        funding_balance = float(self.funding_balance)
        amount = Parsers.parse_float(amount)

        if funding_balance < amount:
            raise exceptions.WalletException(
                ["Insufficient funds"],
                "Insufficient funds in wallet, fund you wallet to continue",
            )

        self.funding_balance = F("funding_balance") - amount
        self.total_balance = F("total_balance") - amount
        self.save()
        self.refresh_from_db(fields=[
            "funding_balance", "total_balance"
        ])

    def withdraw_from_earnings(self, amount):
        earnings_balance = float(self.earnings_balance)
        amount = Parsers.parse_float(amount)

        if earnings_balance < amount:
            raise exceptions.WalletException(
                ["Insufficient funds"],
                "Insufficient funds in wallet, fund you wallet to continue",
            )

        self.earnings_balance = F("earnings_balance") - amount
        self.total_balance = F("total_balance") - amount
        self.save()
        self.refresh_from_db(fields=[
            "earnings_balance", "total_balance"
        ])


# class Bank(models.Model):
#     code = models.CharField(max_length=10, blank=False, null=False)
#     name = models.CharField(max_length=225, blank=False, null=False)

#     def __str__(self):
#         return f"{self.name}"
    