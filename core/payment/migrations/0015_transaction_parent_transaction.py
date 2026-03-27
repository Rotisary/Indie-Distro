from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("payment", "0014_remove_transaction_completed_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="parent_transaction",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="child_transactions",
                to="payment.transaction",
                help_text="Parent transaction used to link related payment steps",
            ),
        ),
    ]
