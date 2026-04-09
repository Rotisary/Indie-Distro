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
    entity_map = {
        "wallet": "wallet",
        "fileprocessingjob": "file_processing",
    }
    entity = entity_map.get(instance.__class__.__name__.lower())
    if not entity:
        raise ValueError(
            f"No websocket entity mapping for {instance.__class__.__name__}"
        )
    status = data.get("status") or ""
    resource_id = data.get("id") or getattr(instance, "pk", "")
    event_payload = {
        "event": event.get("type", ""),
        **data,
    }

    if save:
        EventLog.objects.create(
            user=user,
            type=event.get("type", ""),
            entity=entity,
            status=status,
            resource_id=str(resource_id),
            payload=event_payload,
        )
    try:
        envelope = {
            "type": f"{entity}_event",
            "data": event_payload,
        }
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            user.push_notification_channel_id, envelope
        )
        logger.info(
            f"event emitted: type={event_type}, "
            f"entity={entity}, user={instance.owner.id}"
        )
    except Exception as e:
        logger.error(f"Failed to emit event: {e}")
        raise exceptions.CustomException(message=f"Event emission failed: {e}")


def emit_user_event(
    user,
    event_type: str,
    data: dict,
    *,
    entity: str,
    save: bool = True,
) -> None:
    """
    Emit a websocket event for a user when a resource instance does not exist.
    Event schema: {type, data}
    """
    if not user:
        raise ValueError("User is required for user-scoped events")

    if not entity:
        raise ValueError("Entity is required for user-scoped events")

    event_payload = {
        "event": event_type,
        **(data or {}),
    }
    event = {
        "type": f"{entity}_event",
        "data": event_payload,
    }
    status = (data or {}).get("status") or ""

    if save:
        EventLog.objects.create(
            user=user,
            type=event_type,
            entity=entity,
            status=status,
            resource_id="",
            payload=event_payload,
        )

    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            user.push_notification_channel_id,
            event,
        )
        logger.info(
            f"event emitted: type={event_type}, " f"entity={entity}, user={user.id}"
        )
    except Exception as e:
        logger.error(f"Failed to emit event: {e}")
        raise exceptions.CustomException(message=f"Event emission failed: {e}")
