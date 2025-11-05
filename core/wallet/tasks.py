from celery import shared_task
from loguru import logger
from requests import RequestException

from django.db import transaction

from .models import Wallet
from core.users.models import User
from core.utils.services import FlutterwaveService
from core.utils.helpers.webhook import CreateWebhookEventPayload, trigger_webhooks
from core.utils import enums
from core.utils.exceptions import exceptions


def _handle_error(user, exc):
    logger.error(f"Wallet creation failed for user {user.id}: {str(exc)}")
    trigger_webhooks(
        event_type=enums.WebhookEvent.WALLET_CREATION_FAILED.value,
        payload=CreateWebhookEventPayload.wallet_creation_failed(
            user, "failed to create wallet", kind="client_error"
        )
    ) 


@shared_task(bind=True, max_retries=3, default_retry_delay=60, queue="service")
def create_wallet_for_user(self, user_id: int, *, context: dict=None) -> None:
    user = User.objects.get(id=user_id)
    service = FlutterwaveService()
    try:
        data = service.create_subaccount(
            account_name=f"{user.first_name} {user.last_name}",
            email=user.email,
            mobile_number=user.phone_number,
        )

        with transaction.atomic():
            Wallet.objects.create(
                owner=user,
                account_reference=data['account_reference'],
                barter_id=data['barter_id'],
            )
        logger.info(f"Wallet created successfully for user {user.id}")
        context["wallet_data"] = data
        trigger_webhooks(
            event_type=enums.WebhookEvent.WALLET_CREATION_COMPLETED.value,
            payload=CreateWebhookEventPayload.wallet_creation_completed(user, data)
        )
    except RequestException as exc:
        _handle_error(user, exc)
        raise exc
    except exceptions.CustomException as exc:
        _handle_error(user, exc)
        raise exc           
    except Exception as general_exc:
        # Rollback subaccount creation on Flutterwave if wallet creation fails
        try:
            service.delete_subaccount(account_reference=data['account_reference'])
        except RequestException as exc:
            _handle_error(user, exc)
            raise  
        except exceptions.CustomException:
            _handle_error(user, exc)
            raise 
        raise general_exc
