from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("websocket", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="eventlog",
            name="resource_id",
            field=models.CharField(max_length=100, blank=True, null=True),
        ),
    ]
