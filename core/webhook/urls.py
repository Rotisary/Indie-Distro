from django.urls import path
from .views import FlutterwaveWebhook

urlpatterns = [
    path("flutterwave/", FlutterwaveWebhook.as_view(), name="flutterwave-webhook"),
]