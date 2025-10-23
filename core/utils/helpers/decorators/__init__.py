import hashlib
import json
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
from core.utils.enums import KeyProcessStatus


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
            KeyProcessStatus.SUCCEEDED.value if 200 <= response.status_code < 300 
            else KeyProcessStatus.FAILED.value
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
                        cached.get("status") == KeyProcessStatus.IN_PROGRESS.value 
                        and cached.get("lock_until", 0) > now.timestamp()
                    ):
                        return IdempotencyDecorator._return_response("operation is still being processed")

                    if (
                        cached.get("status") in (
                            KeyProcessStatus.SUCCEEDED.value, KeyProcessStatus.FAILED.value
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
                                "status": KeyProcessStatus.IN_PROGRESS.value,
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
                            record.status == KeyProcessStatus.IN_PROGRESS.value
                            and record.is_locked()
                        ):
                            # Refresh cache
                            cache.set(
                                cache_key, 
                                {
                                    "status": KeyProcessStatus.IN_PROGRESS.value,
                                    "request_hash": record.request_hash,
                                    "lock_until": record.locked_until.timestamp() if record.locked_until else now.timestamp(),
                                }, 
                                timeout=ttl
                            )
                            return IdempotencyDecorator._return_response("operation is still being processed")

                        if (
                            record.status in (
                                KeyProcessStatus.SUCCEEDED.value, KeyProcessStatus.FAILED.value
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
                                KeyProcessStatus.SUCCEEDED.value if 200 <= response.status_code < 300 
                                else KeyProcessStatus.FAILED.value
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