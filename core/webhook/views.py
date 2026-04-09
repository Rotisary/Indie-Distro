from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from loguru import logger
from rest_framework import response, status, views
from rest_framework.parsers import JSONParser

from core.utils.helpers.payment.handlers import PaymentHandlers


class FlutterwaveWebhook(views.APIView):
    authentication_classes = []
    permission_classes = []
    parser_classes = [JSONParser]
    http_method_names = ["post"]

    @method_decorator(csrf_exempt, name="dispatch")
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        secret = getattr(settings, "FLW_WEBHOOK_SECRET", None)
        flw_hash = request.headers.get("Verif-Hash")
        raw_body = request.body

        if secret and flw_hash:
            if secret != flw_hash:
                logger.error("Flutterwave webhook hash mismatch")
                return response.Response(
                    {"status": "error", "detail": "invalid verification hash"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
        elif secret and not flw_hash:
            logger.error("Flutterwave webhook missing verification hash header")
            return response.Response(
                {"status": "error", "detail": "missing verification hash"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = request.data
        event = payload.get("event")
        data = payload.get("data") or {}

        try:
            if event == "charge.completed":
                result = PaymentHandlers.handle_bank_charge(data)
                return response.Response(result, status=status.HTTP_200_OK)
            elif event in ("transfer.completed", "transfer.failed"):
                result = PaymentHandlers.handle_transfer(data)
                return response.Response(result, status=status.HTTP_200_OK)
            else:
                logger.warning(f"Unhandled Flutterwave event: {event}")
                return response.Response(
                    {"status": "ignored"}, status=status.HTTP_200_OK
                )
        except Exception as exc:
            logger.exception(f"Webhook handling failed: {exc}")
            return response.Response(
                {"status": "error", "detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
