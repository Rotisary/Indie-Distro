import hmac
import hashlib

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import views, status, response
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated

from loguru import logger
from drf_spectacular.utils import extend_schema

from .models import WebhookEndpoint
from .serializers import WebhookEndpointSerializer
from core.utils.helpers.authenticators import ServerAuthentication
from core.utils.helpers.payment.handlers import PaymentHandlers


@extend_schema(tags=["webhooks"])
class WebhookEndpointListCreate(views.APIView):
    http_method_names = ["post", "get"]
    authentication_classes = [ServerAuthentication, ]

    @extend_schema(
        description="endpoint to add a new webhook url",
        request=WebhookEndpointSerializer.WebhookListCreate, 
        responses={201: WebhookEndpointSerializer.WebhookListCreate}
    )
    def post(self, request):
        serializer = WebhookEndpointSerializer.WebhookListCreate(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        logger.success(f"webhook endpoint added for user {instance.owner.id} with id: {instance.id}")
        return response.Response(serializer.data, status=status.HTTP_201_CREATED)


    @extend_schema(
        description="get list of webhook endpoints(filter by user or global webhook endpoints)",
        request=None,
        responses={200: WebhookEndpointSerializer.WebhookListCreate(many=True)}
    )
    def get(self, request):
        qs = WebhookEndpoint.objects.filter(owner=request.user) | WebhookEndpoint.objects.filter(owner__isnull=True)
        serializer = WebhookEndpointSerializer(qs, many=True)
        return response.Response(serializer.data)
    

@extend_schema(tags=["webhooks"])
class WebhookEndpointUpdate(views.APIView):
    http_method_names = ["patch", "get"]
    authentication_classes = [ServerAuthentication, ]

    @extend_schema(
        description="endpoint to update a webhook url",
        request=WebhookEndpointSerializer.WebhookUpdate, 
        responses={201: WebhookEndpointSerializer.WebhookListCreate}
    )
    def patch(self, request, pk):
        instance = WebhookEndpoint.objects.get(id=pk)
        serializer = WebhookEndpointSerializer.WebhookUpdate(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        logger.success(f"webhook endpoint updated for user {instance.owner.id} with id: {instance.id}")
        serializer = WebhookEndpointSerializer.WebhookListCreate(instance=instance)
        return response.Response(serializer.data, status=status.HTTP_201_CREATED)


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