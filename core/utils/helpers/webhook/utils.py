import requests
import json, time, uuid
from requests import RequestException

from django.utils import timezone


from core.webhook.models import WebhookEndpoint
from . import SendResult


HEADER_NAME = "verif-key"


class WebhookUtils:

    @staticmethod
    def build_payload(
        event: str, 
        data: dict, 
        webhook_id: str = None, 
        attempt: int = 1
    ) -> tuple[bytes, dict[str, str]]:
        """
        Returns (body_bytes, headers_without_secret)
        """
        webhook_id = webhook_id or str(uuid.uuid4())
        envelope = {
            "id": webhook_id,
            "event": event,
            "created_at": timezone.now().isoformat(),
            "attempt": attempt,
            "data": data,
        }

        body = json.dumps(envelope, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Indie-Distro Webhook/1.0",
            "X-Webhook-Event": event,
            "X-Webhook-Id": webhook_id,
        }
        return body, headers

    @staticmethod
    def _send(endpoint: WebhookEndpoint, event: str, payload: dict, attempt: int) -> SendResult:
        body, headers = WebhookUtils.build_payload(event, payload, attempt=attempt)
        headers[HEADER_NAME] = endpoint.get_secret()

        # merge any custom headers safely
        extra = endpoint.headers or {}
        headers.update({k: str(v) for k, v in extra.items()})

        try:
            resp = requests.post(
                endpoint.target_url,
                data=body,
                headers=headers,
                timeout=(10, 15),
            )
            ok = 200 <= resp.status_code < 300
            return SendResult(status_code=resp.status_code, ok=ok, error=None if ok else resp.text[:500])
        except RequestException as exc:
            return SendResult(status_code=None, ok=False, error=str(exc))