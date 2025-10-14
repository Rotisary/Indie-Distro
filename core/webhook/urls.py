from django.urls import path
from .views import WebhookEndpointListCreate, WebhookEndpointUpdate

urlpatterns = [
    path("endpoints/", WebhookEndpointListCreate.as_view(), name="webhook-endpoints"),
    path("endpoints/<int:pk>", WebhookEndpointUpdate.as_view(), name="webhook-endpoints-update"),
]