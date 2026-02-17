from celery import shared_task


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def initiate_subaccount_transfer_task(self, charge_tx_ref: int, amount: str):
    from core.payment.models import Transaction
    from core.utils.helpers.payment.handlers import PaymentHandlers

    try:
        charge_tx = Transaction.objects.get(id=charge_tx_ref)
        PaymentHandlers._initiate_subaccount_transfer(charge_tx, amount)
    except Exception as exc:
        self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))