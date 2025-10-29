from django.db import models
from django.utils.translation import gettext_lazy as _

from core.utils import mixins


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
    created_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Flutterwave Sub-Account Creation Date"),
        help_text=_("Date when the Flutterwave sub-account was created")
    )
    balance = models.DecimalField(
        default=0,
        max_digits=15,
        decimal_places=2,
        null=False,
        blank=True
    )
    wallet_pin = models.CharField(null=True, blank=True)
                                     

    class Meta:
        verbose_name = _("Wallet")
        verbose_name_plural = _("Wallets")


    def __str__(self):
        return f"{self.owner.email} wallet <{self.id}>"


# class Bank(models.Model):
#     code = models.CharField(max_length=10, blank=False, null=False)
#     name = models.CharField(max_length=225, blank=False, null=False)

#     def __str__(self):
#         return f"{self.name}"
    