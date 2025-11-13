from django.urls import path

from .views import FetchVirtualAccount


urlpatterns = [
    path('<str:pk>/fetch-virtual-account/', FetchVirtualAccount.as_view(), name='fetch-virtual-account'),
]