from rest_framework import views, status, response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from loguru import logger
from drf_spectacular.utils import extend_schema

from .models import Wallet
from .tasks import fetch_virtual_account_for_wallet
from core.utils import exceptions
from core.utils.permissions import IsObjOwner, IsAccountType
from .serializers import FundWalletSerializer, PayoutSerializer, WalletPinSerializer
from core.utils.helpers import payment
from core.utils.helpers.decorators import (
    RequestDataManipulationsDecorators,
    IdempotencyDecorator,
)
from core.utils import enums


@extend_schema(tags=["wallets"])
class FetchVirtualAccount(views.APIView):
    http_method_names = ["get"]
    permission_classes = [IsAuthenticated, IsObjOwner]

    @extend_schema(
        description="endpoint to fetch virtual account details",
        request=None,
        responses={200: FundWalletSerializer.FetchVirtualAccountResponseSerializer()},
    )
    def get(self, request, pk):
        try:
            wallet = Wallet.objects.get(account_reference=pk)
            self.check_object_permissions(request, wallet)
            fetch_virtual_account_for_wallet.delay(wallet.pk)
            logger.success(
                f"virtual account fetch for wallet ({wallet.account_reference}) started"
            )
            return response.Response(
                data={
                    "status": "in progress",
                    "message": f"Virtual account fetch for {wallet.account_reference} has started",
                },
                status=status.HTTP_202_ACCEPTED,
            )
        except Wallet.DoesNotExist:
            raise exceptions.CustomException(
                message="This wallet does not exist",
                status_code=status.HTTP_404_NOT_FOUND,
            )


@extend_schema(tags=["wallets"])
class InitiateFundingWithBankCharge(views.APIView):
    http_method_names = ["post"]
    permission_classes = [IsAuthenticated, IsAccountType.IsCreatorAccount, IsObjOwner]

    @extend_schema(
        description="endpoint to initiate wallet funding",
        request=FundWalletSerializer.InitiateBankChargeFundingSerializer(),
        responses={
            200: FundWalletSerializer.InitiateBankChargeFundingResponseSerializer()
        },
    )
    @RequestDataManipulationsDecorators.update_request_data_with_owner_data("owner")
    @IdempotencyDecorator.make_endpoint_idempotent(ttl=300)
    def post(self, request):
        serializer = FundWalletSerializer.InitiateBankChargeFundingSerializer(
            request.data
        )
        serializer.is_valid(raise_exception=True)
        owner = serializer.validated_data["owner"]
        amount = serializer.validated_data["amount"]
        wallet_pin = serializer.validated_data["wallet_pin"]

        request.user.wallet.verify_pin(wallet_pin)
        entry_lines = [
            {
                "user": owner,
                "account_type": enums.LedgerAccountType.FUNDING.value,
                "entry_type": enums.EntryType.DEBIT.value,
                "amount": amount,
            },
            {
                "user": None,
                "account_type": enums.LedgerAccountType.PROVIDER_WALLET.value,
                "entry_type": enums.EntryType.CREDIT.value,
                "amount": amount,
            },
        ]
        transaction = payment.PostLedgerData.as_pending(
            ledger_data=entry_lines,
            tx_purpose=enums.TransactionPurpose.FUNDING.value,
            description="Wallet funding via bank charge",
        )
        payment_helper = payment.PaymentHelper(
            user=request.user,
            transaction=transaction,
            amount=amount,
            payment_type=enums.PaymentType.BANK_CHARGE.value,
            charge_type="nigerian",
        )
        payment_response = payment_helper.charge_bank()
        status_code = (
            status.HTTP_202_ACCEPTED
            if payment_response.status == "initiated"
            else status.HTTP_502_BAD_GATEWAY
        )

        return response.Response(data=payment_response, status=status_code)


@extend_schema(tags=["wallets"])
class InitiatePayout(views.APIView):
    """
    Initiate a payout from a creator's earnings balance to a bank account.
    Completion/failure is handled asynchronously via Flutterwave transfer webhook.
    """

    http_method_names = ["post"]
    permission_classes = [IsAuthenticated, IsAccountType.IsCreatorAccount, IsObjOwner]

    @extend_schema(
        description="Initiate payout (withdraw from earnings) via transfer",
        request=PayoutSerializer.InitiatePayoutSerializer(),
        responses={200: PayoutSerializer.InitiatePayoutResponseSerializer()},
    )
    @IdempotencyDecorator.make_endpoint_idempotent(ttl=300)
    def post(self, request):
        serializer = PayoutSerializer.InitiatePayoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
        wallet_pin = serializer.validated_data["wallet_pin"]

        request.user.wallet.verify_pin(wallet_pin)
        with transaction.atomic():
            request.user.wallet.withdraw_funds(amount, is_earnings=True)
            beneficiary = {
                "bank": serializer.validated_data["bank"],
                "account_number": serializer.validated_data["account_number"],
                "name": serializer.validated_data.get("name")
                or f"{request.user.first_name} {request.user.last_name}",
            }

            entry_lines = [
                {
                    "user": request.user,
                    "account_type": enums.LedgerAccountType.USER_WALLET.value,
                    "entry_type": enums.EntryType.DEBIT.value,
                    "amount": amount,
                },
                {
                    "user": request.user,
                    "account_type": enums.LedgerAccountType.WITHDRAWAL.value,
                    "entry_type": enums.EntryType.CREDIT.value,
                    "amount": amount,
                },
            ]

            tx = payment.PostLedgerData.as_pending(
                ledger_data=entry_lines,
                tx_purpose=enums.TransactionPurpose.PAYOUT.value,
                description="earnings payout",
            )

        payment_helper = payment.PaymentHelper(
            user=request.user,
            transaction=tx,
            amount=amount,
            payment_type=enums.PaymentType.TRANSFER.value,
        )

        payment_response = payment_helper.transfer(
            beneficiary=beneficiary,
            description="Earnings payout",
            debit_subaccount=request.user.wallet.account_reference,
        )

        status_code = (
            status.HTTP_202_ACCEPTED
            if payment_response.status == "initiated"
            else status.HTTP_502_BAD_GATEWAY
        )
        return response.Response(data=payment_response, status=status_code)


@extend_schema(tags=["wallets"])
class SetWalletPin(views.APIView):
    http_method_names = ["post"]
    permission_classes = [IsAuthenticated, IsObjOwner]

    @extend_schema(
        description="Set wallet PIN",
        request=WalletPinSerializer.SetPin(),
        responses={200: WalletPinSerializer.PinResponse()},
    )
    def post(self, request, pk):
        try:
            wallet = Wallet.objects.get(account_reference=pk)
            self.check_object_permissions(request, wallet)
        except Wallet.DoesNotExist:
            raise exceptions.CustomException(
                message="This wallet does not exist",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = WalletPinSerializer.SetPin(data=request.data)
        serializer.is_valid(raise_exception=True)
        wallet.set_pin(serializer.validated_data["pin"])
        return response.Response(
            data={"status": "success", "message": "Wallet PIN set"},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["wallets"])
class ChangeWalletPin(views.APIView):
    http_method_names = ["post"]
    permission_classes = [IsAuthenticated, IsObjOwner]

    @extend_schema(
        description="Change wallet PIN",
        request=WalletPinSerializer.ChangePin(),
        responses={200: WalletPinSerializer.PinResponse()},
    )
    def post(self, request, pk):
        try:
            wallet = Wallet.objects.get(account_reference=pk)
            self.check_object_permissions(request, wallet)
        except Wallet.DoesNotExist:
            raise exceptions.CustomException(
                message="This wallet does not exist",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = WalletPinSerializer.ChangePin(data=request.data)
        serializer.is_valid(raise_exception=True)
        wallet.verify_pin(serializer.validated_data["old_pin"])
        wallet.set_pin(serializer.validated_data["new_pin"])
        return response.Response(
            data={"status": "success", "message": "Wallet PIN updated"},
            status=status.HTTP_200_OK,
        )
