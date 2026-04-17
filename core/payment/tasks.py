from decimal import Decimal

from celery import shared_task
from loguru import logger

from core.payment.models import Transaction
from core.utils.exceptions import exceptions
from core.utils.helpers.payment import PostLedgerData
from core.utils.services import FlutterwaveService


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
        verification_response = service.verify_transaction(tx_id)

        if verification_response["status"].lower() != "success":
            logger.warning(f"invalid transaction: {tx_ref}. Rejected")
            return {
                "verification": verification_response,
            }

        if (
            verification_response["status"].lower() == "success"
            and verification_response["data.status"].lower() != "successful"
        ):

            error_data = {
                "webhook": webhook_payload,
                "verif_status": verification_response,
            }
            PaymentHandlers._finalise_failed_charge(
                tx, error_data, verification_response
            )
            logger.error(f"Verification failed for tx {tx.reference}")
            return {
                "verification": verification_response,
            }

        success_data = {
            "webhook": webhook_payload,
            "verif_status": verification_response,
        }

        # post successful charge data and handle data posting failure
        try:
            PostLedgerData.as_successful(tx, success_data, "charge")
        except Exception as e:
            # TODO issue refund
            PaymentHandlers._emit_payment_event(tx, success=False)
            logger.warning(f"charge.completed: tx {tx.reference} failed")

        initiate_subaccount_transfer_task.delay(tx_ref, amount)
        logger.info(
            f"Charge verified and subaccount transfer queued for tx={tx.reference}"
        )
        return {
            "verification": verification_response,
        }
    except exceptions.ServiceRequestException as exc:
        logger.error(f"Verification error for charge tx_ref={tx_ref}: {str(exc)}")
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
    Verify a Flutterwave transfer status before finalising it in our ledger.
    """

    from core.utils.helpers.payment.handlers import PaymentHandlers

    try:
        tx = Transaction.objects.get(reference=tx_ref)

        service = FlutterwaveService()
        verification_response = service.verify_transaction(tx_id)

        if verification_response["status"].lower() != "success":
            logger.warning(f"invalid transaction: {tx_ref}. Rejected")
            return {
                "verification": verification_response,
            }

        if (
            verification_response["status"].lower() == "success"
            and verification_response["data.status"].lower() != "successful"
        ):
            error_data = {
                "webhook": webhook_payload,
                "verif_status": verification_response,
            }
            PaymentHandlers._finalise_failed_transfer(
                tx, error_data, verification_response
            )
            logger.error(f"Verification failed for tx {tx.reference}")
            return {
                "verification": verification_response,
            }

        success_data = {
            "webhook": webhook_payload,
            "verif_status": verification_response,
        }
        PaymentHandlers._finalise_successful_transfer(tx, success_data, Decimal(amount))
        logger.info(
            f"Transfer verification and finalisation completed for tx={tx.reference}"
        )
        return {"verification": verification_response}
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


@shared_task(bind=True, max_retries=3)
def handle_virtual_funding_task(
    self, tx_ref: str, tx_id: int, amount: str, webhook_payload: dict
):
    """
    Verify a Flutterwave transfer status before finalising it in our ledger.
    """

    from core.utils.helpers.payment.handlers import PaymentHandlers

    try:
        service = FlutterwaveService()
        verification_response = service.verify_transaction(tx_id)
        if verification_response["status"].lower() != "success":
            logger.warning(f"invalid transaction: {tx_ref}. Rejected")
            return {
                "verification": verification_response,
            }

        tx = PaymentHandlers._create_virtual_funding_entry(webhook_payload)
        if (
            verification_response["status"].lower() == "success"
            and verification_response["data.status"].lower() != "successful"
        ):
            error_data = {
                "webhook": webhook_payload,
                "verif_status": verification_response,
            }
            PaymentHandlers._finalise_failed_transfer(
                tx, error_data, verification_response
            )
            logger.error(f"Verification failed for tx {tx.reference}")
            return {
                "verification": verification_response,
            }

        success_data = {
            "webhook": webhook_payload,
            "verif_status": verification_response,
        }
        PaymentHandlers._finalise_successful_transfer(tx, success_data, Decimal(amount))
        logger.info(
            f"Transfer verification and finalisation completed for tx={tx.reference}"
        )
        return {"verification": verification_response}
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
