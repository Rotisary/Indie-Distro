from rest_framework import views, status, response
from rest_framework.permissions import IsAuthenticated

from loguru import logger
from drf_spectacular.utils import extend_schema

from .models import WebhookEndpoint
from .serializers import WebhookEndpointSerializer
from core.utils.helpers.authenticators import ServerAuthentication


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
    def patch(self, pk, request):
        instance = WebhookEndpoint.objects.get(id=pk)
        serializer = WebhookEndpointSerializer.WebhookUpdate(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        logger.success(f"webhook endpoint updated for user {instance.owner.id} with id: {instance.id}")
        serializer = WebhookEndpointSerializer.WebhookListCreate(instance=instance)
        return response.Response(serializer.data, status=status.HTTP_201_CREATED)
