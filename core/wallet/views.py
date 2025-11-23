from rest_framework import views, status, response
from rest_framework.permissions import IsAuthenticated

from loguru import logger
from drf_spectacular.utils import extend_schema

from .models import Wallet
from .tasks import fetch_virtual_account_for_wallet
from core.utils import exceptions
from core.utils.permissions import IsObjOwner
from .serializers import FundWalletSerializer
from core.utils.helpers import payment
from core.utils.helpers.decorators import RequestDataManipulationsDecorators
from core.utils import enums


@extend_schema(tags=["wallets"])
class FetchVirtualAccount(views.APIView):
    http_method_names = ["get"]
    permission_classes = [IsAuthenticated, IsObjOwner]

    @extend_schema(
        description="endpoint to fetch virtual account details",
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
        

class InitiateFundingWithBankCharge(views.APIView):
    http_method_names = ["post"]
    permission_classes = [IsAuthenticated, ]

    @extend_schema(
        description="endpoint to initiate wallet funding",
        request=FundWalletSerializer.InitiateBankChargeFundingSerializer(), 
        responses={200: FundWalletSerializer.InitiateBankChargeFundingResponseSerializer()}
    )
    @RequestDataManipulationsDecorators.update_request_data_with_owner_data("owner")
    def post(self, request):
        serializer = FundWalletSerializer.InitiateBankChargeFundingSerializer(request.data)
        serializer.is_valid(raise_exception=True)
        owner = serializer.validated_data["owner"]
        amount = serializer.validated_data["amount"]
        entry_lines = [
            {
                "user": owner,
                "account_type": enums.LedgerAccountType.EXTERNAL_FUNDING_WITHDRAWAL.value,
                "entry_type": enums.EntryType.DEBIT,
                "amount": amount
            },
            {
                "user": owner,
                "account_type": enums.LedgerAccountType.USER_WALLET.value,
                "entry_type": enums.EntryType.CREDIT,
                "amount": amount
            }
        ]
        transaction = payment.PostLedgerData.as_pending(
            ledger_data=entry_lines,
            description="Wallet funding via bank charge"
        )
        payment_helper = payment.PaymentHelper(
            user=request.user, 
            transaction=transaction,
            amount=amount,
            payment_type=enums.PaymentType.BANK_CHARGE.value, 
            charge_type="nigerian"
        )
        payment_response = payment_helper.charge_bank()
        status_code = None
        if payment_response.status == "initiated":
            status_code = status.HTTP_200_OK
        else:
            status_code = status.HTTP_502_BAD_GATEWAY
        
        return response.Response(
            data=payment_response, status=status_code
        )