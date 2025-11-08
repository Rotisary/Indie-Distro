"""
Django base settings for paylink project.
"""

import os
from pathlib import Path
from django.utils.timezone import timedelta
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from config.celery.queue import CeleryQueue
from celery.schedules import crontab

from .. import env

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

PRODUCTION = env.bool("PRODUCTION", False)
USE_MEMORY_DATABASE = env.bool("USE_MEMORY_DATABASE", True)
USING_MANAGED_STORAGE = env.bool("USING_MANAGED_STORAGE", False)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str(
    'DJANGO_SECRET_KEY', 'django-insecure-hkp)*xa9#c%txjag9ku7#rgm2^61n+0sy@c!*mzg61q_vb7obw'
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", True)

# ALLOWED_HOSTS = ['localhost', '0.0.0.0', '127.0.0.1', 'c45a-197-211-52-131.ngrok-free.app']

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=[
        "*",
    ],
)


# Application definition

INSTALLED_APPS = [
    # django default apps
    "unfold",
    "unfold.contrib.filters",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # third party apps
    "drf_spectacular",
    "rest_framework",
    "corsheaders",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_celery_beat",
    "django_filters",
]

CORE_APPS = [
    'core.users.apps.UsersConfig',
    'core.payment.apps.PaymentConfig',
    'core.feed.apps.FeedConfig',
    'core.utils.apps.UtilsConfig',
    'core.playback.apps.PlaybackConfig',
    'core.file_storage.apps.FileStorageConfig',
    'core.wallet.apps.WalletConfig',
    'core.webhook.apps.WebhookConfig'
]

INSTALLED_APPS += CORE_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
AUTH_USER_MODEL = "users.User"

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
API_VERSION = env.int("API_VERSION", default=1)

# CORS
CORS_ALLOW_ALL_ORIGINS = env.bool(
    "CORS_ALLOW_ALL_ORIGINS", False
)
CORS_ALLOWED_ORIGINS = env.list(
        "DJANGO_CORS_ALLOWED_ORIGINS",
        default=[],
    )

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
        # "core.utils.permissions.EnforceAccountBan",
    ),
    # "DEFAULT_PARSER_CLASSES": [
    #     "rest_framework.parsers.JSONParser",
    # ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "50/minute"},
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core.utils.exceptions.exceptions.custom_exception_handler",
}

# Schema Spectacular Generator
SPECTACULAR_SETTINGS = {
    "TITLE": "Indie-Distro API",
    "DESCRIPTION": "Film distribution platform for independent filmmakers",
    "VERSION": f"V{API_VERSION}",
    "SERVE_INCLUDE_SCHEMA": False,
}


UNFOLD = {
    "SITE_TITLE": "Indie-Distro Backend",
    "SITE_DESCRIPTION": "Film distribution platform for independent filmmakers",
    "SITE_HEADER": "Indie-Distro",
    "SHOW_HISTORY": True,
    "SIDEBAR": {
        "show_search": True,
        "show-all_applications": True,
        "navigation": [
            {
                "title": _("Users & Session"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Users"),
                        "icon": "person",
                        "link": reverse_lazy("admin:users_user_changelist"),
                    },
                    {
                        "title": _("Sessions"),
                        "icon": "fingerprint",
                        "link": reverse_lazy("admin:users_usersession_changelist"),
                    },
                ],
            },
            {
                "title": _("Feed"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Films"),
                        "icon": "movie",
                        "link": reverse_lazy("admin:feed_feed_changelist"),
                    },
                    {
                        "title": _("Purchases"),
                        "icon": "receipt_long",
                        "link": reverse_lazy("admin:feed_purchase_changelist"),
                    },
                    {
                        "title": _("Shorts"),
                        "icon": "movie",
                        "link": reverse_lazy("admin:feed_short_changelist"),
                    },
                ]
            },
            {
                "title": _("File Storage"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Files"),
                        "icon": "folder",
                        "link": reverse_lazy("admin:file_storage_filemodel_changelist"),
                    },
                    {
                        "title": _("File Processing Jobs"),
                        "icon": "build",
                        "link": reverse_lazy("admin:file_storage_fileprocessingjob_changelist"),
                    },
                ]
            },
            {
                "title": _("Wallets"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Wallets"),
                        "icon": "account_balance_wallet",
                        "link": reverse_lazy("admin:wallet_wallet_changelist"),
                    },
                ]
            },
            {
                "title": _("Payment"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Account"),
                        "icon": "wallet",
                        "link": reverse_lazy("admin:payment_ledgeraccount_changelist"),
                    },
                    {
                        "title": _("Transactions"),
                        "icon": "receipt",
                        "link": reverse_lazy("admin:payment_transaction_changelist"),
                    },
                    {
                        "title": _("Journals"),
                        "icon": "book",
                        "link": reverse_lazy("admin:payment_ledgerjournal_changelist"),
                    },
                    {
                        "title": _("Entries"),
                        "icon": "list",
                        "link": reverse_lazy("admin:payment_ledgerentry_changelist"),
                    },
                ]
            },
            {
                "title": _("Webhooks"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Webhook Endpoints"),
                        "icon": "link",
                        "link": reverse_lazy("admin:webhook_webhookendpoint_changelist"),
                    },
                ]
            }
        ]
    }
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
    "JWK_URL": None,
    "LEEWAY": 0,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(days=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
}
JWT_SECRET = env.str("JWT_SECRET")
WEBHOOK_ENC_KEY = env.str("WEBHOOK_ENC_KEY", default="")

# Chatting & Caches
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"


REDIS_HOST = env.str("REDIS_HOST", default="localhost")
REDIS_PORT = env.int("REDIS_PORT", default=6379)

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}",
    }
}

PRESIGNED_UPLOAD_TTL = 60*60

CELERY_BROKER = env.str("CELERY_BROKER")
CELERY_BROKER_URL = CELERY_BROKER
CELERY_RESULT_BACKEND = env.str("CELERY_BACKEND")
CELERY_TIMEZONE = env.str("CELERY_TIMEZONE", default="UTC")
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERYD_PREFETCH_MULTIPLIER = 1
CELERY_QUEUES = CeleryQueue.queues()


CELERY_BEAT_SCHEDULE = {
    "clear_out_expired_periodic_tasks": {
        "task": "core.utils.tasks.clear_out_periodic_tasks",
        "schedule": crontab(hour="*/2"),
        "options": {"queue": "beats"},
    },
    "clear_out_all_blacklisted_tokens": {
        "task": "core.utils.tasks.clear_out_blacklisted_tokens",
        "schedule": crontab(hour="0,12", minute=0),
        "options": {"queue": "beats"},
    },
    "reconcile-due-releases": {
        "task": "core.feed.tasks.reconcile_due_releases",
        "schedule": crontab(minute="*"),
        "options": {"queue": "beats"},
    },
    "delete_expired_idempotency_keys": {
        "task": "core.utils.tasks.delete_expired_idempotency_keys",
        "schedule": crontab(minute="*"),
        "options": {"queue": "beats"},
    },
}


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'webhook.log',
        },
    },
    'loggers': {
        '': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

if USING_MANAGED_STORAGE:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

    AWS_ACCESS_KEY_ID = env.str("DJANGO_AWS_ACCESS_KEY_ID", "*****")
    AWS_SECRET_ACCESS_KEY = env.str("DJANGO_AWS_SECRET_ACCESS_KEY", "*****")
    AWS_STORAGE_BUCKET_NAME = env.str("DJANGO_AWS_STORAGE_BUCKET_NAME", "*****")

    AWS_S3_FILE_OVERWRITE = True
    AWS_S3_REGION_NAME = env.str("DJANGO_AWS_S3_REGION_NAME", "lon1")
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_DEFAULT_ACL = None
    AWS_S3_ADDRESSING_STYLE = "virtual"
    AWS_S3_ENDPOINT_URL = "https://lon1.digitaloceanspaces.com"
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.lon1.digitaloceanspaces.com"
    # AWS_QUERYSTRING_AUTH = True

    # DO_SPACE_URL_TIMEOUT_SECS = env.int(
    #     "DJANGO_AWS_S3_CACHE_CONTROL_TIMEOUT_SECS", 3600
    # )
    # AWS_S3_OBJECT_PARAMETERS = {"CacheControl": f"max-age={DO_SPACE_URL_TIMEOUT_SECS}"}

    PUBLIC_MEDIA_LOCATION = "media"
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{PUBLIC_MEDIA_LOCATION}/"


SERVER_SECRET_KEY_FIELD_NAME = env.str(
    "DJANGO_SERVER_SECRET_KEY_FIELD_NAME", "SECRET_KEY"
)

SERVER_SECRET_KEY = env.str("DJANGO_SERVER_SECRET_KEY", "**************")

IDEMPOTENCY_KEY_HEADER_NAME = env.str(
    "IDEMPOTENCY_KEY_HEADER_NAME", "IDEMPOTENCY_KEY"
)