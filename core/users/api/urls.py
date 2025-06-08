from django.urls import path
from .views import (
    register,
    user_detail_view,
    update_user_detail_view,
    delete_user_view,
    ObtainAuthTokenView,
    PasswordChangeView,
    update_wallet_view,
    # wallet_view
)

urlpatterns = [
    # user urls
    path('register/', register, name='register'),
    path('details/<str:username>/', user_detail_view, name='user-detail'),
    path('details/<str:username>/update/', update_user_detail_view, name='details-update'),
    path('<str:username>/delete/', delete_user_view, name='delete-user'),
    path('login/', ObtainAuthTokenView.as_view(), name='login'),
    path('change-password/', PasswordChangeView.as_view(), name='change-password'),

    # wallet urls
    path('wallet/<str:id>/update/', update_wallet_view, name='update-wallet'),
    # path('wallet/<str:wallet_id>/', wallet_view, name='wallet-detail')
]
