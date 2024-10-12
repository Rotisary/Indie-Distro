from django.urls import path
from payment.api.views import send_money, transaction_detail

urlpatterns = [
    path('send-money/', send_money, name='send-money'),
    path('transaction/<str:transaction_id>/', transaction_detail, name='transaction-detail')
]