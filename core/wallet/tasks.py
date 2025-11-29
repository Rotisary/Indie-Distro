from celery import shared_task
from loguru import logger
from requests import RequestException

from django.db import transaction

from .models import Wallet
from core.users.models import User
from core.utils.services import FlutterwaveService
from core.utils.exceptions import exceptions
from core.utils.helpers.decorators import UpdateObjectStatusDecorator


@shared_task(bind=True, max_retries=3, default_retry_delay=60, queue="service")
@UpdateObjectStatusDecorator.wallet_creation(
    server_exceptions=(
        RequestException, 
        Exception, 
        exceptions.CustomException
    ),    
)
def create_wallet_for_user(
        self, user_id: int, **kwargs
    ) -> None:
    user = User.objects.get(id=user_id)
    service = FlutterwaveService()
    try:
        data = service.create_subaccount(
            account_name=f"{user.first_name} {user.last_name}",
            email=user.email,
            mobile_number=user.phone_number,
        )

        with transaction.atomic():
            wallet = Wallet.objects.create(
                owner=user,
                account_reference=data['account_reference'],
                barter_id=data['barter_id'],
            )
        logger.info(f"Wallet created successfully for user {user.id}")
        kwargs["context"]["wallet_id"] = wallet.pk
    except RequestException as exc:
        logger.error(f"Wallet creation failed for user {user.id}: {str(exc)}")
        raise exc
    except exceptions.CustomException as exc:
        logger.error(f"Wallet creation failed for user {user.id}: {str(exc)}")
        raise exc           
    except Exception as general_exc:
        # Rollback subaccount creation on Flutterwave if wallet creation fails
        try:
            service.delete_subaccount(account_reference=data['account_reference'])
        except RequestException as exc:
            logger.error(f"Wallet creation failed for user {user.id}: {str(exc)}")
            raise  
        except exceptions.CustomException:
            logger.error(f"Wallet creation failed for user {user.id}: {str(exc)}")
            raise 
        logger.error(f"Wallet creation failed for user {user.id}: {str(exc)}")
        raise general_exc



@shared_task(bind=True, max_retries=3, default_retry_delay=60, queue="service")
@UpdateObjectStatusDecorator.virtual_account_fetch(
    server_exceptions=(
        RequestException, 
        Exception, 
        exceptions.CustomException
    ),    
)
def fetch_virtual_account_for_wallet(
        self, wallet_pk: str
    ) -> None:
    wallet = Wallet.objects.get(pk=wallet_pk)
    service = FlutterwaveService()
    try:
        service.fetch_static_virtual_account(
            account_reference=wallet.account_reference,
            wallet=wallet
        )
        logger.info(f"Virtual account fetched successfully for wallet {wallet.id}")
    except RequestException as exc:
        logger.error(f"Virtual account fetch failed for wallet {wallet.id}: {str(exc)}")
        raise exc
    except exceptions.CustomException as exc:
        logger.error(f"Virtual account fetch failed for wallet {wallet.id}: {str(exc)}")
        raise exc
    except Exception as exc:
        logger.error(f"Virtual account fetch failed for wallet {wallet.id}: {str(exc)}")
        raise exc