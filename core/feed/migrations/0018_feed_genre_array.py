import django.contrib.postgres.fields
from django.db import migrations, models


def wrap_genre_in_array(apps, schema_editor):
    Feed = apps.get_model("feed", "Feed")
    for feed in Feed.objects.all().only("id", "genre"):
        if feed.genre is None:
            feed.genre = []
        elif isinstance(feed.genre, str):
            feed.genre = [feed.genre]
        feed.save(update_fields=["genre"])


def unwrap_genre_from_array(apps, schema_editor):
    Feed = apps.get_model("feed", "Feed")
    for feed in Feed.objects.all().only("id", "genre"):
        if not feed.genre:
            feed.genre = ""
        else:
            feed.genre = feed.genre[0]
        feed.save(update_fields=["genre"])


class Migration(migrations.Migration):

    dependencies = [
        ("feed", "0017_alter_short_slug"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE feed_feed "
                        "ALTER COLUMN genre TYPE varchar(100)[] "
                        "USING ARRAY[genre];"
                    ),
                    reverse_sql=(
                        "ALTER TABLE feed_feed "
                        "ALTER COLUMN genre TYPE varchar(100) "
                        "USING genre[1];"
                    ),
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="feed",
                    name="genre",
                    field=django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(
                            choices=[
                                ("Action", "ACTION"),
                                ("Drama", "DRAMA"),
                                ("Romance", "ROMANCE"),
                                ("Horror", "HORROR"),
                                ("Sci-Fi", "SCI_FI"),
                                ("Fantasy", "FANTASY"),
                                ("Thriller", "THRILLER"),
                                ("Comedy", "COMEDY"),
                            ],
                            max_length=100,
                        ),
                        blank=False,
                        default=list,
                        help_text="The genres that the film falls under",
                        null=False,
                        size=None,
                        verbose_name="Film Genre",
                    ),
                ),
            ],
        ),
        migrations.RunPython(wrap_genre_in_array, unwrap_genre_from_array),
    ]
