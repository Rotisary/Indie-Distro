from channels.generic.websocket import AsyncJsonWebsocketConsumer
from loguru import logger


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def _send_event(self, event):
        event_type = event.get("type") if isinstance(event, dict) else None
        data = event.get("data") if isinstance(event, dict) else None
        if not event_type or not isinstance(data, dict):
            logger.warning(f"Malformed websocket event: {event}")
            return

        if "event" not in data:
            logger.warning(f"Malformed websocket event payload: {event}")
            return

        await self.send_json({"type": event_type, "data": data})

    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.group_name = self.user.push_notification_channel_id
        await self.accept()
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.send_json({
            "type": "connection_established",
            "message": "Connected to notification service",
            "user_id": self.user.id,
        })
        logger.info(f"WebSocket connected user={self.user.id}")

    async def disconnect(self, close_code):
        if getattr(self, "group_name", None):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info(f"WebSocket disconnected code={close_code}")

    async def receive_json(self, data, **kwargs):
        message_type = data.get("type")
        if message_type == "ping":
            await self.send_json({"type": "pong", "timestamp": data.get("timestamp")})
            return

        if message_type in {"subscribe", "unsubscribe"}:
            group = data.get("group")
            if group:
                if group != self.user.push_notification_channel_id:
                    await self.send_json({
                        "type": "error",
                        "message": "Unauthorized group subscription",
                    })
                    return
                if message_type == "subscribe":
                    await self.channel_layer.group_add(group, self.channel_name)
                else:
                    await self.channel_layer.group_discard(group, self.channel_name)
                await self.send_json({"type": "ack", "group": group})
            return

        await self.send_json({"type": "error", "message": "Unknown message type"})

    async def wallet_event(self, event):
        await self._send_event(event)

    async def file_processing_event(self, event):
        await self._send_event(event)

    async def payment_event(self, event):
        await self._send_event(event)
