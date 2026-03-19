from django.urls import path

from .views import (
    FetchVirtualAccount,
    InitiateFundingWithBankCharge,
    WalletStatusPollView,
    VirtualAccountFetchPollView,
    InitiatePayout,
    SetWalletPin,
    ChangeWalletPin,
)


urlpatterns = [
    path('<str:pk>/fetch-virtual-account/', FetchVirtualAccount.as_view(), name='fetch-virtual-account'),
    path('fund-with-bank-charge/', InitiateFundingWithBankCharge.as_view(), name='fund-with-bank-charge '),
    path('<str:pk>/status/', WalletStatusPollView.as_view(), name='wallet-status-poll'),
    path('<str:pk>/virtual-account/status/', VirtualAccountFetchPollView.as_view(), name='virtual-account-fetch-poll'),
    path('<str:pk>/pin/set/', SetWalletPin.as_view(), name='set-wallet-pin'),
    path('<str:pk>/pin/change/', ChangeWalletPin.as_view(), name='change-wallet-pin'),
    path('payouts/initiate/', InitiatePayout.as_view(), name='initiate-payout'),
]