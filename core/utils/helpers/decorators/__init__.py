import hashlib
import json
import inspect
from functools import wraps
from datetime import timedelta
from typing import Callable, Optional

from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.conf import settings
from django.http import QueryDict


from rest_framework.response import Response
from rest_framework import status as http_status

from core.utils.models import IdempotencyKey
from core.utils import enums
from core.utils.helpers.webhook import CreateWebhookEventPayload, trigger_webhooks


class RequestDataManipulationsDecorators:
    @staticmethod
    def extract_all_request_data_to_kwargs(function):
        """
        extract data in queryset to kwargs
        """

        def function_to_execute(self, request, *args, **kwargs):
            if request.method.lower() == "get":
                request_data = request.GET
            else:
                request_data = request.data

            for key, value in request_data.items():
                kwargs[key] = value

            return function(self, request, *args, **kwargs)

        function_to_execute.__name__ = function.__name__
        return function_to_execute

    @staticmethod
    def extract_required_data_to_kwargs(function):
        def function_to_execute(self, request, *args, **kwargs):
            required_fields = self.get_required_fields()
            if request.method.lower() == "get":
                request_data = request.GET
            else:
                request_data = request.data

            for field in required_fields:
                kwargs[field] = request_data.get(field)
            return function(self, request, *args, **kwargs)

        function_to_execute.__name__ = function.__name__
        return function_to_execute

    @staticmethod
    def update_request_data_with_owner_data(owner_field_name="owner"):
        def inner(function):
            def function_to_execute(self, request, *args, **kwargs):
                if isinstance(request.data, QueryDict):
                    request.data._mutable = True
                request.data[owner_field_name] = request.user.id
                return function(self, request, *args, **kwargs)

            function_to_execute.__name__ = function.__name__
            return function_to_execute

        return inner

    @staticmethod
    def mutable_request_data(function):
        def function_to_execute(self, request, *args, **kwarg):
            if isinstance(request.data, QueryDict):
                request.data._mutable = True
            return function(self, request, *args, **kwarg)

        function_to_execute.__name__ = function.__name__
        return function_to_execute
    

class IdempotencyDecorator:

    @staticmethod
    def _hash_body(data) -> str:
        if data is None:
            b = b""
        elif isinstance(data, (bytes, bytearray)):
            b = bytes(data)
        else:
            b = json.dumps(
                data, 
                sort_keys=True, 
                separators=(",", ":"), 
                ensure_ascii=False
            ).encode("utf-8")
        return hashlib.sha256(b).hexdigest()


    @staticmethod
    def _cache_key(
            namespace: str, 
            user_id: Optional[int], 
            idem_key: str
        ) -> str:
        uid = user_id if user_id is not None else "anon"
        return f"{namespace}:{uid}:{idem_key}"


    @staticmethod
    def _return_response(message: str, response_status=http_status.HTTP_409_CONFLICT):
        return Response({"detail": message}, status=response_status)
    

    @staticmethod
    def _persist_db(idem_key: IdempotencyKey, response, *, now, expires_at):
        idem_key.status = (
            enums.KeyProcessStatus.SUCCEEDED.value if 200 <= response.status_code < 300 
            else enums.KeyProcessStatus.FAILED.value
        )
        idem_key.response_status = response.status_code
        idem_key.response_body = getattr(response, "data", None)
        idem_key.locked_until = now
        idem_key.expires_at = expires_at
        idem_key.save(update_fields=[
                "status", 
                "response_status", 
                "response_body", 
                "locked_until", 
                "expires_at", 
                "date_last_modified"
            ])


    @staticmethod
    def make_endpoint_idempotent(ttl: int = 24 * 3600, lock_for: int = 60, namespace: str = "idem"):
        """
        makes an endpoint idempotent:
        - saves keys and response data to cache and DB.
        - For read, looks through cache first and checks DB if there is a miss.
        """
        def inner(function):
            def function_to_execute(self, request, *args, **kwargs):
                idempotency_key = request.headers.get(settings.IDEMPOTENCY_KEY_HEADER_NAME) or None
                if not idempotency_key:
                    return function(self, request, *args, **kwargs)

                now = timezone.now()
                body_hash = IdempotencyDecorator._hash_body(getattr(request, "data", None))
                user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
                user_id = getattr(user, "id", None)
                cache_key = IdempotencyDecorator._cache_key(namespace, user_id, idempotency_key)
           
                # check cache for idempotency key
                cached = cache.get(cache_key)
                if cached:
                    if cached.get("request_hash") and cached["request_hash"] != body_hash:
                        return IdempotencyDecorator._return_response("Idempotency key conflict (different payload)")

                    if ( 
                        cached.get("status") == enums.KeyProcessStatus.IN_PROGRESS.value 
                        and cached.get("lock_until", 0) > now.timestamp()
                    ):
                        return IdempotencyDecorator._return_response("operation is still being processed")

                    if (
                        cached.get("status") in (
                            enums.KeyProcessStatus.SUCCEEDED.value, enums.KeyProcessStatus.FAILED.value
                        ) 
                        and "response_status" in cached
                    ):
                        return Response(cached.get("response_body") or {}, status=cached.get("response_status"))

                # check DB is there is a cache miss
                locked_until = now + timedelta(seconds=lock_for)
                expires_at = now + timedelta(seconds=ttl)

                try:
                    with transaction.atomic():
                        record = IdempotencyKey.objects.create(
                            key=idempotency_key,
                            user=user,
                            request_hash=body_hash,
                            locked_until=locked_until,
                            expires_at=expires_at,
                        )                    

                        # set cache
                        cache.set(
                            cache_key,
                            {
                                "status": enums.KeyProcessStatus.IN_PROGRESS.value,
                                "request_hash": body_hash,
                                "lock_until": locked_until.timestamp(),
                            }, 
                            timeout=ttl
                        )
                except IntegrityError:
                    with transaction.atomic():
                        record = (
                            IdempotencyKey.objects
                            .select_for_update(skip_locked=True)
                            .filter(key=idempotency_key, user=user)
                            .first()
                        )
                        if not record:
                            return IdempotencyDecorator._return_response("operation is still being processed")

                        if record.request_hash and record.request_hash != body_hash:
                            return IdempotencyDecorator._return_response("Idempotency key conflict (different payload)")

                        if ( 
                            record.status == enums.KeyProcessStatus.IN_PROGRESS.value
                            and record.is_locked()
                        ):
                            # Refresh cache
                            cache.set(
                                cache_key, 
                                {
                                    "status": enums.KeyProcessStatus.IN_PROGRESS.value,
                                    "request_hash": record.request_hash,
                                    "lock_until": record.locked_until.timestamp() if record.locked_until else now.timestamp(),
                                }, 
                                timeout=ttl
                            )
                            return IdempotencyDecorator._return_response("operation is still being processed")

                        if (
                            record.status in (
                                enums.KeyProcessStatus.SUCCEEDED.value, enums.KeyProcessStatus.FAILED.value
                            )
                            and record.response_status
                        ):
                            # Populate cache and return cached response
                            cache.set(
                                cache_key, 
                                {
                                    "status": record.status,
                                    "request_hash": record.request_hash,
                                    "response_status": record.response_status,
                                    "response_body": record.response_body,
                                    "lock_until": now.timestamp(),
                                }, 
                                timeout=ttl
                            )
                            return Response(record.response_body or {}, status=record.response_status)
            
                response: Response = function(self, request, *args, **kwargs)

                # Persist result to DB, then cache it
                try:
                    with transaction.atomic():
                        idem_key = IdempotencyKey.objects.select_for_update().get(pk=record.pk)
                        IdempotencyDecorator._persist_db(idem_key, response, now=now, expires_at=expires_at)
                finally:
                    cache.set(
                        cache_key, 
                        {
                            "status": (
                                enums.KeyProcessStatus.SUCCEEDED.value if 200 <= response.status_code < 300 
                                else enums.KeyProcessStatus.FAILED.value
                            ),
                            "request_hash": body_hash,
                            "response_status": response.status_code,
                            "response_body": getattr(response, "data", None),
                            "lock_until": now.timestamp(),
                        }, 
                        timeout=ttl
                    )

                return response
            
            function_to_execute.__name__ = function.__name__
            return function_to_execute
        return inner
    

class WebhookTriggerDecorator:
    """
    Decorator to wrap functions that triggers webhooks based on success or failure.
    Usage:
      @WebhookDecorator.file_processing(
          client_exceptions=(ValidationError,),
          server_exceptions=(requests.RequestException, Exception),
      )
      def step(..., trigger_webhook: bool = False):
          ...

    Pass trigger_webhook=True at call-time to actually send webhooks.
    """

    @staticmethod
    def _bind_view_args(function, self_obj, args, kwargs) -> dict:
        sig = inspect.signature(function)
        bound = sig.bind_partial(self_obj, *args, **kwargs)
        bound.apply_defaults()
        return dict(bound.arguments)
    
    @staticmethod
    def _build_file_processing_payload():
        def success(args):           
            return CreateWebhookEventPayload.job_processing_completed(args["job_id"])
        
        def client_error(exc, args):
            return CreateWebhookEventPayload.job_processing_failed(
                args["job_id"], error_message=str(exc), kind="client_error" 
            )
        
        def server_error(args):
            return CreateWebhookEventPayload.job_processing_failed(
                args["job_id"], error_message="internal server error", kind="server_error"
            )
        return success, client_error, server_error
    

    @staticmethod
    def _build_wallet_creation_payload():
        def success(args):           
            return CreateWebhookEventPayload.wallet_creation_completed(
                args["user_id"], data=args["data"]
            )
        
        def client_error(exc, args):
            return CreateWebhookEventPayload.wallet_creation_failed(
                args["user_id"], error_message=str(exc), kind="client_error" 
            )
        
        def server_error(args):
            return CreateWebhookEventPayload.wallet_creation_failed(
                args["user_id"], error_message="internal server error", kind="server_error"
            )
        return success, client_error, server_error


    @staticmethod
    def _wrap(
        success_event: str,
        fail_event: str,
        client_exceptions: tuple[type[BaseException], ...],        
        server_exceptions: tuple[type[BaseException], ...], 
        payload_builder: Callable,     
    ):
        def inner(function):
            def function_to_execute(self, *args, **kwargs):
                context = kwargs.setdefault("context", {})
                trigger = kwargs.pop("trigger_webhook", False)
                if not trigger:
                    return function(self, *args, **kwargs)

                bound = WebhookTriggerDecorator._bind_view_args(function, self, args, kwargs)
                # build arguments for payload builders
                args = {
                    "job_id": bound.get("job_id") or None,
                    "user_id": bound.get("user_id") or getattr(bound.get("user"), "id", None),
                    "data": kwargs.get("context", {}).get("wallet_data") if "context" in kwargs else None,                   
                }
                success, client_error, server_error = payload_builder()
                try:
                    response = function(self, *args, **kwargs)
                except client_exceptions as exc:
                    payload = client_error(exc, args)
                    trigger_webhooks(
                        event_type=fail_event,
                        payload=payload
                    )
                    raise
                except server_exceptions as exc:
                    payload = server_error(args)
                    trigger_webhooks(
                        event_type=fail_event,
                        payload=payload
                    )
                    raise
                else:
                    payload = success(args)
                    trigger_webhooks(
                        event_type=success_event,
                        payload=payload,
                    )
                    return response
            function_to_execute.__name__ = function.__name__
            return function_to_execute
        return inner


    @staticmethod
    def file_processing(
        *,
        success_event: str = enums.WebhookEvent.PROCESSING_COMPLETED.value,
        fail_event: str = enums.WebhookEvent.PROCESSING_FAILED.value,
        client_exceptions: tuple[type[BaseException], ...],
        server_exceptions: tuple[type[BaseException], ...],
    ):
        return WebhookTriggerDecorator._wrap(
            success_event=success_event,
            fail_event=fail_event,
            client_exceptions=client_exceptions,
            server_exceptions=server_exceptions,
            payload_builder=WebhookTriggerDecorator._build_file_processing_payload
        )
    

    @staticmethod
    def wallet_creation(
        *,
        success_event: str = enums.WebhookEvent.WALLET_CREATION_COMPLETED.value,
        fail_event: str = enums.WebhookEvent.WALLET_CREATION_FAILED.value,
        client_exceptions: tuple[type[BaseException], ...],
        server_exceptions: tuple[type[BaseException], ...],
    ):
        return WebhookTriggerDecorator._wrap(
            success_event=success_event,
            fail_event=fail_event,
            client_exceptions=client_exceptions,
            server_exceptions=server_exceptions,
            payload_builder=WebhookTriggerDecorator._build_file_processing_payload
        )