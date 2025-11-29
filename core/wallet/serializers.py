from rest_framework import serializers
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
            help_text=_("The user that wants to fund their wallet.")
        )
        amount = serializers.DecimalField(
            required=True, 
            max_digits=17, 
            decimal_places=2,
            help_text=_("The amount to fund the wallet with.")
        )
    
    class InitiateBankChargeFundingResponseSerializer(serializers.Serializer):
        status = serializers.CharField(
            read_only=True, help_text=_("The status of the funding initiation")
        )
        data = serializers.DictField(read_only=True)
        error = serializers.CharField(read_only=True)
        message = serializers.CharField(read_only=True)


class WalletPollSerializer:

    class WalletPollResponseSerializer(serializers.Serializer):
        status = serializers.CharField(read_only=True)
        owner = serializers.IntegerField(read_only=True)
        wallet = serializers.DictField(
            read_only=True,
            help_text=_(
                "contains the details of the wallet that was created(account reference, barter id)"
            )
        )

    class VirtualAccountFetchPollResponseSerializer(serializers.Serializer):
        status = serializers.CharField(read_only=True)
        owner = serializers.IntegerField(read_only=True)
        virtual_account = serializers.DictField(
            read_only=True,
            help_text=_(
                "contains the details of the virtual account that was fetched(bank name, code and number)"
            )
        )
