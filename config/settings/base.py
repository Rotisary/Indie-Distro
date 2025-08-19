"""
Django base settings for paylink project.
"""

import os
from pathlib import Path
from django.utils.timezone import timedelta
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

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
]

CORE_APPS = [
    'core.users.apps.UsersConfig',
    'core.payment.apps.PaymentConfig',
    'core.feed.apps.FeedConfig',
    'core.utils.apps.UtilsConfig',
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