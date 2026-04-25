from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("payment", "0015_transaction_finalisation_state"),
        ("payment", "0015_transaction_parent_transaction"),
    ]

    operations = []
