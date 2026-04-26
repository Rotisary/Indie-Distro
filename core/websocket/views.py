from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import response, serializers, status, views
from rest_framework.permissions import IsAuthenticated

from core.utils import exceptions

from .models import EventLog


@extend_schema(tags=["Websocket Events"])
class EventReplayView(views.APIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get"]

    @extend_schema(
        description="Get the last N websocket events for the authenticated user.",
        parameters=[
            OpenApiParameter(
                name="limit",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Number of recent events to return. Min 1, max 200, default 50.",
            )
        ],
        responses={
            200: inline_serializer(
                name="EventReplayResponseItem",
                fields={
                    "type": serializers.CharField(),
                    "data": serializers.DictField(),
                    "timestamp": serializers.CharField(),
                },
                many=True,
            )
        },
    )
    def get(self, request):
        limit_param = request.query_params.get("limit", 50)
        try:
            limit = int(limit_param)
        except (TypeError, ValueError):
            raise exceptions.CustomException(message="Invalid limit value")
        limit = max(1, min(limit, 200))
        events = EventLog.objects.filter(user=request.user)[:limit]
        payload = [
            {
                "type": e.type,
                "data": e.payload,
                "timestamp": e.created_at.isoformat(),
            }
            for e in events
        ]
        return response.Response(payload, status=status.HTTP_200_OK)
