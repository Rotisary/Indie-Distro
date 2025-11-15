from rest_framework import views, status, response
from rest_framework.permissions import IsAuthenticated

from loguru import logger
from drf_spectacular.utils import extend_schema

from .models import Wallet
from .tasks import fetch_virtual_account_for_wallet
from core.utils import exceptions
from core.utils.permissions import IsObjOwner
from .serializers import FundWalletSerializer


@extend_schema(tags=["wallets"])
class FetchVirtualAccount(views.APIView):
    http_method_names = ["get"]
    permission_classes = [IsAuthenticated, IsObjOwner]

    @extend_schema(
        description="endpoint to add a new webhook url",
        request=None, 
        responses={200: FundWalletSerializer.FetchVirtualAccountResponseSerializer()}
    )
    def get(self, request, pk):
        try:
            wallet = Wallet.objects.get(account_reference=pk)
            self.check_object_permissions(request, wallet)
            fetch_virtual_account_for_wallet.delay(wallet.pk)
            logger.success(f"virtual account fetch for wallet ({wallet.account_reference}) started")
            return response.Response(data={
                    "status": "in progress",
                    "message": f"Virtual account fetch for {wallet.account_reference} has started"
                }, 
                status=status.HTTP_200_OK
            )
        except Wallet.DoesNotExist:
            raise exceptions.CustomException(
                message="This wallet does not exist",
                status_code=status.HTTP_404_NOT_FOUND
            )