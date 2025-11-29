from django.urls import path

from .views import (
    FetchVirtualAccount,
    InitiateFundingWithBankCharge,
    WalletStatusPollView,
    VirtualAccountFetchPollView
)


urlpatterns = [
    path('<str:pk>/fetch-virtual-account/', FetchVirtualAccount.as_view(), name='fetch-virtual-account'),
    path('fund-with-bank-charge/', InitiateFundingWithBankCharge.as_view(), name='fund-with-bank-charge '),
    path('<str:pk>/status/', WalletStatusPollView.as_view(), name='wallet-status-poll'),
    path('<str:pk>/virtual-account/status/', VirtualAccountFetchPollView.as_view(), name='virtual-account-fetch-poll'),
]