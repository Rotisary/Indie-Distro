from django.conf import settings
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from loguru import logger
from rest_framework import response, status, views
from rest_framework.parsers import JSONParser

from core.utils import enums
from core.utils.helpers.payment.handlers import PaymentHandlers
from core.webhook.models import ProviderWebhookEvent


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
        tx_ref = data.get("reference") or data.get("tx_ref")
        provider_event_id = data.get("id")
        provider_status = data.get("status").lower()
        idempotency_key = (
            f"{enums.WebhookProvider.FLUTTERWAVE.value}:"
            f"{event}:{provider_event_id}:{tx_ref}:{provider_status}"
        )

        webhook_event, created = ProviderWebhookEvent.objects.get_or_create(
            idempotency_key=idempotency_key,
            defaults={
                "provider": enums.WebhookProvider.FLUTTERWAVE.value,
                "event": event or "",
                "tx_ref": tx_ref,
                "provider_event_id": (
                    str(provider_event_id) if provider_event_id else None
                ),
                "provider_status": provider_status,
                "payload": payload,
            },
        )

        if not created and webhook_event.processing_state in (
            enums.WebhookProcessingState.ACKNOWLEDGED.value,
            enums.WebhookProcessingState.IGNORED.value,
        ):
            stored_response = webhook_event.handler_response or {
                "status": "already_processed"
            }
            return response.Response(stored_response, status=status.HTTP_200_OK)

        try:
            if event == "charge.completed":
                result = PaymentHandlers.handle_bank_charge(data)
            elif event in (
                "transfer.completed",
                "transfer.disburse",
                "transfer.failed",
            ):
                result = PaymentHandlers.handle_transfer_event(data)
            else:
                logger.warning(f"Unhandled Flutterwave event: {event}")
                result = {"status": "ignored"}
                webhook_event.processing_state = (
                    enums.WebhookProcessingState.IGNORED.value
                )
                webhook_event.handler_response = result
                webhook_event.processed_at = timezone.now()
                webhook_event.save(
                    update_fields=[
                        "processing_state",
                        "handler_response",
                        "processed_at",
                    ]
                )
                return response.Response(result, status=status.HTTP_200_OK)

            webhook_event.processing_state = (
                enums.WebhookProcessingState.ACKNOWLEDGED.value
            )
            webhook_event.handler_response = result
            webhook_event.processed_at = timezone.now()
            webhook_event.save(
                update_fields=["processing_state", "handler_response", "processed_at"]
            )
            return response.Response(result, status=status.HTTP_200_OK)
        except Exception as exc:
            webhook_event.processing_state = enums.WebhookProcessingState.FAILED.value
            webhook_event.handler_response = {
                "status": "error",
                "detail": str(exc),
            }
            webhook_event.processed_at = timezone.now()
            webhook_event.save(
                update_fields=["processing_state", "handler_response", "processed_at"]
            )
            logger.exception(f"Webhook handling failed: {exc}")
            return response.Response(
                {"status": "error", "detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
