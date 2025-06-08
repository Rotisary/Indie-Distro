"""
WSGI config for paylink project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os
import django
from dotenv import load_dotenv

load_dotenv()

from django.core.wsgi import get_wsgi_application

django.setup()
os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    os.getenv('DJANGO_SETTINGS_MODULE', 'config.settings.prod'))

application = get_wsgi_application()
