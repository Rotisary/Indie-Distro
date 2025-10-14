from rest_framework import views, status, response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from .models import WebhookEndpoint
from .serializers import WebhookEndpointSerializer


@extend_schema(tags=["webhooks"])
class WebhookEndpointListCreate(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="endpoint to add a new webhook url",
        request=WebhookEndpointSerializer, 
        responses={201: WebhookEndpointSerializer}
    )
    def post(self, request):
        data = request.data.copy()
        data["owner"] = request.user.id
        serializer = WebhookEndpointSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return response.Response(WebhookEndpointSerializer(instance).data, status=status.HTTP_201_CREATED)


    @extend_schema(
        responses={200: WebhookEndpointSerializer(many=True)}
    )
    def get(self, request):
        qs = WebhookEndpoint.objects.filter(owner=request.user) | WebhookEndpoint.objects.filter(owner__isnull=True)
        serializer = WebhookEndpointSerializer(qs, many=True)
        return response.Response(serializer.data)

