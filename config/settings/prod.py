from .base import *

PRODUCTION = True

DATABASES = {
    "default": {
        "ENGINE": os.getenv(
            "POSTGRESQL_ENGINE", "django.db.backends.postgresql_psycopg2"
        ),
        "NAME": os.getenv("POSTGRES_NAME", "***"),
        "USER": os.getenv("POSTGRES_USER", "***"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "***"),
        "HOST": os.getenv("POSTGRES_HOST", "*****"),
        "PORT": os.getenv("POSTGRES_PORT", 5432),
    },
}