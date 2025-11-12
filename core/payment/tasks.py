from celery import shared_task
from loguru import logger
from requests import RequestException

from django.db import transaction
from rest_framework import status

from .models import LedgerAccount, Transaction, LedgerEntry, LedgerJournal
from core.users.models import User
from core.utils.services import FlutterwaveService
from core.utils.exceptions import exceptions
from core.utils.helpers.decorators import WebhookTriggerDecorator
from core.utils import enums


@shared_task(bind=True, max_retries=3, default_retry_delay=60, queue="service")
@WebhookTriggerDecorator.bank_charge(
    client_exceptions=(
        exceptions.ClientPaymentException
    ),
    server_exceptions=(
        RequestException, 
        Exception, 
        exceptions.CustomException
    ),  
)
def charge_nigerian_account(
    self, user_id: int, amount, tx_reference: str, **kwargs
) -> None:
    try:
        user = User.objects.get(id=user_id)
        tx = Transaction.objects.get(reference=tx_reference)
        if tx.status == enums.TransactionStatus.SUCCESSFUL.value:
            logger.info(
                f"transaction with reference: {tx.reference} already processed successfully"
            )
            return 
        elif tx.status != enums.TransactionStatus.PENDING.value:
            logger.info(
                f"transaction with reference: {tx.reference} cannot be processed again"
            )
            raise exceptions.ClientPaymentException(
                message=f"""The transaction ({tx.reference}) cannot be processed. 
                        It has either failed or has been cancelled""",
                errors="Invalid Transaction Reference"
            )
        
        try:
            service = FlutterwaveService()
            data = service.charge_nigerian_bank(
                user=user,
                amount=amount,
                tx_reference=tx_reference
            )
            logger.success("nigerian bank charge initiated")
            tx.status = enums.TransactionStatus.INITIATED.value
            tx.metadata = data
            tx.save(update_fields=["status", "metadata"])
            kwargs["context"]["payment_data"]["charge_data"] = data["meta"]
        except (
            RequestException, 
            exceptions.CustomException, 
            exceptions.ClientPaymentException
        ) as exc:
            logger.error(f"nigerian account charge failed ({tx.reference}): {str(exc)}")
            raise exc       
    except User.DoesNotExist:
        raise exceptions.ClientPaymentException(
            message=f"The specified user ({user.id}) does not exist",
            errors="Invalid User"
        )
    except Transaction.DoesNotExist:
        logger.error(f"nigerian account charge failed ({tx.reference}): {str(exc)}")
        raise exceptions.CustomException(
            message="Invalid transaction reference",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )