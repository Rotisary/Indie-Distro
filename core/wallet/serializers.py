from rest_framework import serializers
from django.utils.translation import gettext_lazy as _ 

from core.users.models import User

class FundWalletSerializer:

    class FetchVirtualAccountResponseSerializer(serializers.Serializer):
        status = serializers.CharField(read_only=True)
        message = serializers.CharField(read_only=True)
