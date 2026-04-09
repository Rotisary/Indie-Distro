from django.urls import path

from .views import (
    ChangeWalletPin,
    FetchVirtualAccount,
    InitiateFundingWithBankCharge,
    InitiatePayout,
    SetWalletPin,
)

urlpatterns = [
    path(
        "<str:pk>/fetch-virtual-account/",
        FetchVirtualAccount.as_view(),
        name="fetch-virtual-account",
    ),
    path(
        "fund-with-bank-charge/",
        InitiateFundingWithBankCharge.as_view(),
        name="fund-with-bank-charge ",
    ),
    path("<str:pk>/pin/set/", SetWalletPin.as_view(), name="set-wallet-pin"),
    path("<str:pk>/pin/change/", ChangeWalletPin.as_view(), name="change-wallet-pin"),
    path("payouts/initiate/", InitiatePayout.as_view(), name="initiate-payout"),
]
