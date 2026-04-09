from drf_spectacular.utils import extend_schema
from rest_framework import response, status, views
from rest_framework.permissions import IsAuthenticated

from .models import EventLog


@extend_schema(tags=["Websocket Events"])
class EventReplayView(views.APIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get"]

    @extend_schema(description="Get the last N events for the authenticated user")
    def get(self, request):
        limit = int(request.query_params.get("limit", 50))
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
