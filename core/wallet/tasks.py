from celery import shared_task
from loguru import logger

from django.db import transaction

from .models import Wallet
from core.users.models import User
from core.utils.services import FlutterwaveService


@shared_task(bind=True, max_retries=3, default_retry_delay=60, queue="service")
def create_wallet_for_user(self, user_id: int) -> None:
    user = User.objects.get(id=user_id)
    service = FlutterwaveService()
    data = service.create_subaccount(
        account_name=f"{user.first_name} {user.last_name}",
        email=user.email,
        mobile_number=user.phone_number,
    )

    try:
        with transaction.atomic():
            Wallet.objects.create(
                owner=user,
                account_reference=data['account_reference'],
                barter_id=data['barter_id'],
            )
    except Exception as e:
        # Rollback subaccount creation on Flutterwave if wallet creation fails
        service.delete_subaccount(account_reference=data['account_reference'])
        logger.error(f"Wallet creation failed for user {user.id}: {str(e)}")
        raise e
    
    logger.info(f"Wallet created successfully for user {user.id}")