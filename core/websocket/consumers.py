from channels.generic.websocket import AsyncJsonWebsocketConsumer
from loguru import logger


class NotificationConsumer(AsyncJsonWebsocketConsumer):
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
                if message_type == "subscribe":
                    await self.channel_layer.group_add(group, self.channel_name)
                else:
                    await self.channel_layer.group_discard(group, self.channel_name)
                await self.send_json({"type": "ack", "group": group})
            return

        await self.send_json({"type": "error", "message": "Unknown message type"})

    async def notify(self, event):
        await self.send_json(event.get("event", {}))
