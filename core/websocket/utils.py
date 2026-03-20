from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from loguru import logger

from .models import EventLog
from core.utils import exceptions


def emit_websocket_event(instance, event_type: str, save: bool = True) -> None:
    """
    Emit a websocket event using the instance.EventData.on_<event_type> builder.
    Event schema: {type, data}
    """
    event_method = getattr(instance.EventData, f"on_{event_type}", None)
    if not event_method:
        raise ValueError(f"Unknown websocket event type: {event_type}")

    event = event_method(instance)
    user = getattr(instance, "owner", None)
    if not user:
        raise ValueError("Event instance does not have an owner")

    data = event.get("data") or {}
    entity = instance.__class__.__name__.lower()
    status = data.get("status") or ""
    resource_id = data.get("id") or getattr(instance, "pk", "")

    if save:
        EventLog.objects.create(
            user=user,
            type=event.get("type", ""),
            entity=entity,
            status=status,
            resource_id=str(resource_id),
            payload=data,
        )
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            user.push_notification_channel_id,
            event
        )
        logger.info(
            f"event emitted: type={event_type}, "
            f"user={instance.owner.id}"
        )
    except Exception as e:
        logger.error(f"Failed to emit event: {e}")
        raise exceptions.CustomException(
            message=f"Event emission failed: {e}"
        )


def emit_user_event(user, event_type: str, data: dict, save: bool = True) -> None:
    """
    Emit a websocket event for a user when a resource instance does not exist.
    Event schema: {type, data}
    """
    if not user:
        raise ValueError("User is required for user-scoped events")

    event = {
        "type": event_type,
        "data": data or {},
    }
    status = (data or {}).get("status") or ""

    if save:
        EventLog.objects.create(
            user=user,
            type=event_type,
            entity="user",
            status=status,
            resource_id="",
            payload=event.get("data") or {},
        )

    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            user.push_notification_channel_id,
            event,
        )
        logger.info(
            f"event emitted: type={event_type}, "
            f"user={user.id}"
        )
    except Exception as e:
        logger.error(f"Failed to emit event: {e}")
        raise exceptions.CustomException(
            message=f"Event emission failed: {e}"
        )
