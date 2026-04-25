from django.db import migrations, models

BANK_CHARGE = "bank_charge"
TRANSFER = "transfer"


def backfill_transaction_type(apps, schema_editor):
    Transaction = apps.get_model("payment", "Transaction")
    JournalEntry = apps.get_model("payment", "JournalEntry")

    for tx in Transaction.objects.all().iterator():
        metadata = tx.metadata or {}

        tx_type = None

        if tx.parent_transaction_id:
            tx_type = TRANSFER
        elif tx.purpose == "payment":
            tx_type = TRANSFER
        elif metadata.get("transfer_initiation_data") or metadata.get(
            "flw_transfer_webhook"
        ):
            tx_type = TRANSFER
        elif metadata.get("charge_initiation_data") or metadata.get(
            "flw_charge_webhook"
        ):
            tx_type = BANK_CHARGE
        else:
            account_types = set(
                JournalEntry.objects.filter(journal__transaction=tx).values_list(
                    "account__type", flat=True
                )
            )

            if "external payment" in account_types:
                tx_type = BANK_CHARGE
            elif "withdrawal" in account_types:
                tx_type = TRANSFER
            elif "provider wallet" in account_types and "funding" in account_types:
                tx_type = BANK_CHARGE
            elif "user wallet" in account_types:
                tx_type = TRANSFER

        if not tx_type:
            tx_type = BANK_CHARGE

        Transaction.objects.filter(pk=tx.pk).update(type=tx_type)


def reverse_backfill_transaction_type(apps, schema_editor):
    Transaction = apps.get_model("payment", "Transaction")
    Transaction.objects.update(type=None)


class Migration(migrations.Migration):

    dependencies = [
        ("payment", "0016_merge_0015_payment_heads"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="type",
            field=models.CharField(
                blank=True,
                choices=[("bank_charge", "BANK_CHARGE"), ("transfer", "TRANSFER")],
                help_text="The type of transaction(bank_charge/transfer)",
                max_length=20,
                null=True,
            ),
        ),
        migrations.RunPython(
            backfill_transaction_type,
            reverse_backfill_transaction_type,
        ),
        migrations.AlterField(
            model_name="transaction",
            name="type",
            field=models.CharField(
                choices=[("bank_charge", "BANK_CHARGE"), ("transfer", "TRANSFER")],
                help_text="The type of transaction(bank_charge/transfer)",
                max_length=20,
            ),
        ),
    ]
