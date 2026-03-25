from celery import shared_task
from loguru import logger
from decimal import Decimal

from core.payment.models import Transaction
from core.utils.helpers.payment import PostLedgerData
from core.utils.services import FlutterwaveService
from core.utils.exceptions import exceptions



@shared_task(bind=True)
def initiate_subaccount_transfer_task(self, charge_tx_ref: str, amount: str):
    """
    Trigger the subaccount transfer flow after a verified successful charge.
    """
    from core.utils.helpers.payment.handlers import PaymentHandlers

    try:
        charge_tx = Transaction.objects.get(reference=charge_tx_ref)
        PaymentHandlers._initiate_subaccount_transfer(charge_tx, Decimal(amount))
    except Exception as exc:
        logger.exception(
            f"Error initiating subaccount transfer for transaction={charge_tx_ref}: {exc}"
        )


@shared_task(bind=True, max_retries=3)
def verify_charge_and_initiate_subaccount_transfer_task(
    self, tx_ref: str, tx_id: int, amount: str, webhook_payload: dict
):
    """
    Verify a successful Flutterwave charge before marking it successful
    and initiating the subaccount transfer.
    """
    from core.utils.helpers.payment.handlers import PaymentHandlers

    try:
        tx = Transaction.objects.get(reference=tx_ref)

        service = FlutterwaveService()
        verification_response = service.verify_charge(tx_id)

        if verification_response.lower() not in ["success", "successful"]:
            error_data = {"webhook": webhook_payload, "verif_status": verification_response}
            PaymentHandlers._finalise_failed_charge(tx, error_data, verification_response)
            logger.error(f"Verification failed for tx {tx.reference}")
            return {
                "verification": verification_response,
            }

        success_data = {"webhook": webhook_payload, "verif_status": verification_response}
        PostLedgerData.as_successful(tx, success_data, "charge")
        initiate_subaccount_transfer_task.delay(tx_ref, amount)
        logger.info(
            f"Charge verified and subaccount transfer queued for tx={tx.reference}"
        )
        return {
            "verification": verification_response,
        }
    except exceptions.ServiceRequestException as exc:
        logger.error(
            f"Verification error for charge tx_ref={tx_ref}: {str(exc)}"
        )
        delay = 5 * (self.request.retries + 1)
        raise self.retry(exc=exc, countdown=delay)
    except Exception as exc:
        logger.exception(
            f"Unexpected error in verify_charge_and_initiate_subaccount_transfer_task "
            f"for tx_id={tx_id}: {exc}"
        )
        raise


@shared_task(bind=True, max_retries=3)
def verify_transfer_and_finalize_task(
    self, tx_ref: str, tx_id: int, amount: str, webhook_payload: dict
):
    """
    Verify a successful Flutterwave transfer before finalising it in our ledger.
    """

    from core.utils.helpers.payment.handlers import PaymentHandlers

    try:
        tx = Transaction.objects.get(reference=tx_ref)

        service = FlutterwaveService()
        verification_response = service.verify_transfer(tx_id)
        if verification_response.lower() not in ["success", "successful"]:
            error_data = {"webhook": webhook_payload, "verif_status": verification_response}
            PaymentHandlers._finalise_failed_transfer(tx, error_data, verification_response)
            logger.error(f"Verification failed for tx {tx.reference}")
            return {
                "verification": verification_response,
            }

        success_data = {"webhook": webhook_payload, "verif_status": verification_response}
        PaymentHandlers._finalise_successful_transfer(
            tx, success_data, Decimal(amount)
        )
        logger.info(
            f"Transfer verification and finalisation completed for tx={tx.reference}"
        )
        return {
            "verification": verification_response
        }
    except (exceptions.ServiceRequestException,) as exc:
        logger.error(
            f"Verification error for transfer tx_id={tx_id}: {getattr(exc, 'message', str(exc))}"
        )
        delay = 5 * (self.request.retries + 1)
        raise self.retry(exc=exc, countdown=delay)
    except Exception as exc:
        logger.exception(
            f"Unexpected error in verify_transfer_and_finalize_task "
            f"for tx_id={tx_id}: {exc}"
        )
        raise