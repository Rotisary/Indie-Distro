from rest_framework import serializers
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

from core.users.models import User


class FundWalletSerializer:

    class FetchVirtualAccountResponseSerializer(serializers.Serializer):
        status = serializers.CharField(read_only=True)
        message = serializers.CharField(read_only=True)

    class InitiateBankChargeFundingSerializer(serializers.Serializer):
        owner = serializers.PrimaryKeyRelatedField(
            queryset=User.objects.all(),
            required=True,
            help_text=_("The user that wants to fund their wallet."),
        )
        amount = serializers.DecimalField(
            required=True,
            max_digits=17,
            decimal_places=2,
            help_text=_("The amount to fund the wallet with."),
        )
        wallet_pin = serializers.CharField(
            required=True,
            write_only=True,
            validators=[RegexValidator(r"^\d{4}$", "PIN must be exactly 4 digits")],
            help_text=_("4-digit wallet PIN for payout authorization"),
        )

    class InitiateBankChargeFundingResponseSerializer(serializers.Serializer):
        status = serializers.CharField(
            read_only=True, help_text=_("The status of the funding initiation")
        )
        data = serializers.DictField(read_only=True)
        error = serializers.CharField(read_only=True)
        message = serializers.CharField(read_only=True)


class PayoutSerializer:
    class InitiatePayoutSerializer(serializers.Serializer):
        amount = serializers.DecimalField(
            required=True,
            max_digits=17,
            decimal_places=2,
            help_text=_("Amount to withdraw from earnings"),
        )
        wallet_pin = serializers.CharField(
            required=True,
            write_only=True,
            validators=[RegexValidator(r"^\d{4}$", "PIN must be exactly 4 digits")],
            help_text=_("4-digit wallet PIN for payout authorization"),
        )
        bank = serializers.CharField(
            required=True,
            help_text=_("Beneficiary bank code (Flutterwave bank identifier)"),
        )
        account_number = serializers.CharField(
            required=True,
            help_text=_("Beneficiary account number"),
        )
        name = serializers.CharField(
            required=False,
            allow_blank=True,
            help_text=_("Beneficiary name (optional)"),
        )

    class InitiatePayoutResponseSerializer(serializers.Serializer):
        status = serializers.CharField(read_only=True)
        data = serializers.DictField(read_only=True)
        error = serializers.CharField(read_only=True)
        message = serializers.CharField(read_only=True)


class WalletPinSerializer:
    class SetPin(serializers.Serializer):
        pin = serializers.CharField(
            required=True,
            write_only=True,
            validators=[RegexValidator(r"^\d{4}$", "PIN must be exactly 4 digits")],
            help_text=_("4-digit wallet PIN"),
        )

    class ChangePin(serializers.Serializer):
        old_pin = serializers.CharField(
            required=True,
            write_only=True,
            validators=[RegexValidator(r"^\d{4}$", "PIN must be exactly 4 digits")],
            help_text=_("Current 4-digit wallet PIN"),
        )
        new_pin = serializers.CharField(
            required=True,
            write_only=True,
            validators=[RegexValidator(r"^\d{4}$", "PIN must be exactly 4 digits")],
            help_text=_("New 4-digit wallet PIN"),
        )

    class PinResponse(serializers.Serializer):
        status = serializers.CharField(read_only=True)
        message = serializers.CharField(read_only=True)
