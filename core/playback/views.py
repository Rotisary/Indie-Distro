from rest_framework import status, decorators, response, views
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticated

from loguru import logger
from drf_spectacular.utils import extend_schema

from .serializers import PurchaseIDSerializer
from core.feed.models import Purchase
from core.utils.enums import PurchaseStatusType
from core.utils.exceptions import CustomException
from core.utils.helpers.playback import AccessUtils


class RetrievePlaybackURL(views.APIView):
    http_method_names = ["post", ]
    parser_classes = [JSONParser, ]


    @extend_schema(
        description="endpoint to get playback url for cdn",
        request=PurchaseIDSerializer,
        responses={200, None}
    )
    def post(self, request):
        serializer = PurchaseIDSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        purchase_id = serializer.validated_data["purchase_id"]

        user = request.user
        token = AccessUtils.return_playback_token(purchase_id, user)
        playback_url = f"https://www.cdn.example.com/?token={token}"
        return response.Response(
            data={"url": playback_url}, status=status.HTTP_200_OK
        )
    


class RefreshPlaybackToken(views.APIView):
    http_method_names = ["post", ]
    parser_classes = [JSONParser, ]


    @extend_schema(
        description="endpoint to get playback url for cdn",
        request=PurchaseIDSerializer,
        responses={200, None}
    )
    def post(self, request):
        serializer = PurchaseIDSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        purchase_id = serializer.validated_data["purchase_id"]

        user = request.user
        token = AccessUtils.return_playback_token(purchase_id, user)
        return response.Response(
            data={"token": token}, status=status.HTTP_200_OK
        )