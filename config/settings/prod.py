from .base import *

DATABASES = {
    "default": {
        "ENGINE": env.str(
            "DJANGO_POSTGRESQL_ENGINE", "django.db.backends.postgresql_psycopg2"
        ),
        "NAME": env.str("DJANGO_POSTGRES_NAME", "***"),
        "USER": env.str("DJANGO_POSTGRES_USER", "***"),
        "PASSWORD": env.str("DJANGO_POSTGRES_PASSWORD", "***"),
        "HOST": env.str("DJANGO_POSTGRES_HOST", "*****"),
        "PORT": env.int("DJANGO_POSTGRES_PORT", 5432),
    },
}