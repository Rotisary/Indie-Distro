from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("feed", "0019_purchase_method"),
    ]

    operations = [
        migrations.AddField(
            model_name="feed",
            name="release_task_id",
            field=models.CharField(
                max_length=255,
                null=True,
                blank=True,
                help_text="Celery task id scheduled to release this film",
                verbose_name="Release Task Id",
            ),
        ),
        migrations.AddField(
            model_name="feed",
            name="scheduled_release_at",
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text="Datetime this film is scheduled to be released",
                verbose_name="Scheduled Release At",
            ),
        ),
        migrations.AddField(
            model_name="short",
            name="release_task_id",
            field=models.CharField(
                max_length=255,
                null=True,
                blank=True,
                help_text="Celery task id scheduled to release this short",
                verbose_name="Release Task Id",
            ),
        ),
        migrations.AddField(
            model_name="short",
            name="scheduled_release_at",
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text="Datetime this short is scheduled to be released",
                verbose_name="Scheduled Release At",
            ),
        ),
    ]
