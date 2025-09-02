from rest_framework import status, decorators, response, views
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticated

from loguru import logger
from drf_spectacular.utils import extend_schema


class RetrievePlaybackURL(views.APIView):
    pass

