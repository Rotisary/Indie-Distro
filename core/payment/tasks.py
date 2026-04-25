from datetime import timedelta
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from celery import shared_task
from loguru import logger

from core.payment.models import Transaction
from core.utils import enums
from core.utils.exceptions import exceptions
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
                tx, error_data, verification_response["data.status"]
            )
            logger.error(f"Verification failed for tx {tx.reference}")
            return {
                "verification": verification_response,
            }

        success_data = {
            "webhook": webhook_payload,
            "verif_status": verification_response,
        }
        successful = PaymentHandlers._post_successful_charge(
            tx, success_data, verification_response["data.status"]
        )
        if not successful:
            logger.info(
                f"Charge success verification posting for tx={tx.reference} failed"
            )
            return {
                "verification": verification_response,
            }

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
                tx, error_data, verification_response["data.status"]
            )
            logger.error(f"Verification failed for tx {tx.reference}")
            return {
                "verification": verification_response,
            }

        success_data = {
            "webhook": webhook_payload,
            "verif_status": verification_response,
        }
        PaymentHandlers._finalise_successful_transfer(
            tx, success_data, Decimal(amount), verification_response["data.status"]
        )
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
                tx, error_data, verification_response["data.status"]
            )
            logger.error(f"Verification failed for tx {tx.reference}")
            return {
                "verification": verification_response,
            }

        success_data = {
            "webhook": webhook_payload,
            "verif_status": verification_response,
        }
        PaymentHandlers._finalise_successful_transfer(
            tx, success_data, Decimal(amount), verification_response["data.status"]
        )
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
def reconcile_flutterwave_finalization_failures(self, batch_size: int = 100):
    """
    Reconcile transactions that are stuck in pending/initiated states,
    or not in finalized state.
    """

    from core.utils.helpers.payment.handlers import PaymentHandlers

    try:
        threshold = timezone.now() - timedelta(minutes=2)
        candidates = (
            Transaction.objects.filter(
                Q(finalisation_state__in=PaymentHandlers.NOT_FINALISED_STATES)
                | Q(
                    status__in=[
                        enums.TransactionStatus.PENDING.value,
                        enums.TransactionStatus.INITIATED.value,
                    ],
                    metadata__provider_outcome__isnull=False,
                )
            )
            .filter(date_added__lte=threshold)
            .exclude(finalisation_state__in=PaymentHandlers.FINALIZED_STATES)
            .order_by("date_added")[:batch_size]
        )

        processed = 0
        for tx in candidates:
            try:
                PaymentHandlers.reconcile_transaction_finalization(tx.reference)
                processed += 1
            except Exception as per_tx_err:
                logger.exception(
                    f"Reconciliation failed for tx={tx.reference}: {str(per_tx_err)}"
                )

        logger.info(
            f"Reconciliation run completed. processed={processed} candidates={len(candidates)}"
        )
        return {"processed": processed, "candidates": len(candidates)}
    except exceptions.ServiceRequestException as exc:
        logger.error(f"Reconciliation error: {str(exc)}")
        delay = 5 * (self.request.retries + 1)
        raise self.retry(exc=exc, countdown=delay)
    except Exception as exc:
        logger.exception(
            f"Unexpected error in reconcile_flutterwave_finalization_failures: {str(exc)}"
        )
        raise
