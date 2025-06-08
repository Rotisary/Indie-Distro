# import os
from .base import *

PRODUCTION = False

# INSTALLED_APPS += ["debug_toolbar"]


INTERNAL_IPS = ["127.0.0.1"]

if os.getenv("USE_MEMORY_DATABASE", True):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

else:
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


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATIC_URL = "/static/"

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"


# DB_NAME = 'paylink_db'
# DB_USER = 'django'
# PASSWORD = 'password'
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql_psycopg2',
#         'NAME': DB_NAME,
#         'USER': DB_USER,
#         'PASSWORD': PASSWORD,
#         'HOST': 'localhost',
#         'PORT': 5432
#     }
# }