import os
import uuid
from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from django.db.models import JSONField
from django.core.validators import MinValueValidator

from core.utils.mixins import BaseModelMixin
from core.utils import enums
from core.users.models import User


class LedgerAccount(BaseModelMixin):
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("Ledger Account Owner"),
        related_name="ledger_accounts",
        null=True,
        blank=True
    )
    type = models.CharField(
        _("Ledger Account Type"), 
        choices=enums.LedgerAccountType.choices(), 
        max_length=50,
        null=False, 
        blank=False
    )
    currency = models.CharField(
        _("currency"),
        null=False,
        blank=False,
        max_length=3,
        choices=enums.SupportedCurrency.choices(),
    )

    class Meta:
        verbose_name = _("Ledger Account")
        verbose_name_plural = _("Ledger Accounts")
        unique_together = [("owner", "type", "currency")]

    
    def __str__(self):
        return f"{self.owner.first_name} ({self.type})"


class Transaction(BaseModelMixin):
    reference = models.CharField(
        _("Transaction Reference"), 
        null=False, 
        blank=False,
        unique=True, 
        max_length=15
    )
    status = models.CharField(
        _("Transaction Status"), 
        choices=enums.TransactionStatus.choices(),
        default=enums.TransactionStatus.PENDING.value,
        null=False, 
        blank=False, 
        max_length=20
    )
    description = models.CharField(
        blank=True, null=True, max_length=50
    )
    currency = models.CharField(
        _("currency"),
        null=False,
        blank=False,
        max_length=3,
        choices=enums.SupportedCurrency.choices(),
    )
    metadata = JSONField(
        _("Metadata"), 
        null=True, 
        blank=True,
        default=dict
    )
    completed_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text=_("Date and Time the transaction was marked as completed") 
    )

    class Meta:
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")


    def __str__(self):
        return f"{self.reference} ({self.status})"


class LedgerJournal(BaseModelMixin):
    transaction = models.OneToOneField(
        "Transaction", 
        on_delete=models.PROTECT, 
        related_name="journal",
        null=False,
        blank=False
    )

    class Meta:
        verbose_name = _("Ledger Entry")
        verbose_name_plural = _("Ledger Entries")


class JournalEntry(BaseModelMixin):
    account = models.ForeignKey(
        to="LedgerAccount",
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="entries",
        help_text=_("Ledger account that the money was moved out of or into")
    )
    journal = models.ForeignKey(
        to="LedgerJournal",
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    line_no = models.PositiveIntegerField()
    type = models.CharField(
        choices=enums.EntryType.choices(),
        null=False,
        blank=False,
        verbose_name=_("Entry Type")
    )
    status = models.CharField(
        choices=enums.EntryStatus.choices(),
        default=enums.EntryStatus.PENDING.value,
        null=False,
        blank=False,
        verbose_name=_("Entry Status")     
    )
    amount = models.DecimalField(
        _("Entry Amount"), 
        decimal_places=2, 
        max_digits=17,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    completed_at = models.DateTimeField(
        blank=True, null=True, help_text=_("Date and Time the entry was marked as completed") 
    )

    class Meta:
        verbose_name = _("Ledger Entry")
        verbose_name_plural = _("Ledger Entries")

        unique_together = [("journal", "line_no")]

    def __str__(self):
        return f"{self.account.type} ({self.journal.id}-{self.type})-{self.status}"