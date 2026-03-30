from celery import shared_task
from loguru import logger
from requests import RequestException, Timeout, ConnectionError

from django.db import transaction
from django.utils import timezone

from .models import Wallet
from core.users.models import User
from core.utils.services import FlutterwaveService
from core.utils.exceptions import exceptions
from core.utils import enums
from core.websocket.utils import emit_user_event


@shared_task(bind=True, max_retries=3, queue="service")
def create_wallet_for_user(self, user_id: int) -> None:
    user = User.objects.get(id=user_id)
    service = FlutterwaveService()
    wallet = None
    data = None
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
            wallet.creation_status = enums.WalletCreationStatus.COMPLETED.value
            wallet.save(update_fields=["creation_status", "date_last_modified"])
        logger.info(f"Wallet created successfully for user {user.id}")
        wallet.emit_event(enums.WalletEventType.WALLET_CREATED)
    except (Timeout, ConnectionError) as exc:
        if self.request.retries >= self.max_retries:
            logger.error(
                f"Wallet creation failed for user {user.id}: {str(exc)}. Max retries exceeded"
            )
            emit_user_event(
                user,
                enums.WalletEventType.WALLET_FAILED.value,
                {
                    "status": enums.WalletCreationStatus.FAILED.value,
                    "user_id": user.id,
                    "timestamp": timezone.now().isoformat(),
                },
                entity="wallet",
            )
            raise exc

        logger.error(
            f"Wallet creation failed for user {user.id}: {str(exc)}. Retrying"
        )
        emit_user_event(
            user,
            enums.WalletEventType.WALLET_RETRYING.value,
            {
                "status": enums.WalletCreationStatus.RETRYING.value,
                "user_id": user.id,
                "attempt": self.request.retries + 1,
                "timestamp": timezone.now().isoformat(),
            },
            entity="wallet",
        )
        delay = 5 * (self.request.retries + 1)
        raise self.retry(exc=exc, countdown=delay)
    except (exceptions.ServiceRequestException, RequestException) as exc:
        emit_user_event(
            user,
            enums.WalletEventType.WALLET_FAILED.value,
            {
                "status": enums.WalletCreationStatus.FAILED.value,
                "user_id": user.id,
                "timestamp": timezone.now().isoformat(),
            },
            entity="wallet",
        )
        logger.error(f"Wallet creation failed for user {user.id}: {str(exc)}")
        raise
    except Exception as general_exc:
        # Rollback subaccount creation on Flutterwave if wallet creation fails
        if data and data.get("account_reference"):
            try:
                service.delete_subaccount(account_reference=data['account_reference'])
            except (Timeout, ConnectionError) as exc:
                if self.request.retries >= self.max_retries:
                    logger.error(
                        f"Wallet deletion failed for user {user.id}: {str(exc)}. Max retries exceeded"
                    )
                    raise exc
                logger.error(
                    f"Wallet deletion failed for user {user.id}: {str(exc)}. Retrying"
                )
                delay = 5 * (self.request.retries + 1)
                raise self.retry(exc=exc, countdown=delay)
            except (exceptions.ServiceRequestException, RequestException) as exc:
                logger.error(
                    f"Wallet deletion failed for user {user.id}: {str(exc)}"
                )
                raise exc
        
        emit_user_event(
            user,
            enums.WalletEventType.WALLET_FAILED.value,
            {
                "status": enums.WalletCreationStatus.FAILED.value,
                "user_id": user.id,
                "timestamp": timezone.now().isoformat(),
            },
            entity="wallet",
        )
        logger.error(f"Wallet creation failed for user {user.id}: {str(general_exc)}")
        raise general_exc



@shared_task(bind=True, max_retries=3, queue="service")
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
        wallet.emit_event(enums.WalletEventType.VIRTUAL_ACCOUNT_FETCHED.value)
    except (Timeout, ConnectionError) as exc:
        if self.request.retries >= self.max_retries:
            logger.error(
                f"Virtual account fetch failed for wallet {wallet.id}: {str(exc)}. Max retries exceeded"
            )
            wallet.emit_event(enums.WalletEventType.VIRTUAL_ACCOUNT_FAILED.value)
            raise exc
        logger.error(f"Virtual account fetch failed for wallet {wallet.id}: {str(exc)}. Retrying")
        wallet.emit_event(enums.WalletEventType.VIRTUAL_ACCOUNT_RETRYING.value)
        delay = 5 * (self.request.retries + 1)
        raise self.retry(exc=exc, countdown=delay)
    except (exceptions.ServiceRequestException, RequestException) as exc:
        logger.error(f"Virtual account fetch failed for wallet {wallet.id}: {str(exc)}")
        wallet.emit_event(enums.WalletEventType.VIRTUAL_ACCOUNT_FAILED.value)
        raise
    except (Exception, exceptions.CustomException) as exc:
        logger.error(f"Virtual account fetch failed for wallet {wallet.id}: {str(exc)}")
        wallet.emit_event(enums.WalletEventType.VIRTUAL_ACCOUNT_FAILED.value)
        raise