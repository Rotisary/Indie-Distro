import hashlib
import json
import inspect
from functools import wraps
from datetime import timedelta
from typing import Callable, Optional

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.conf import settings
from django.http import QueryDict


from rest_framework.response import Response
from rest_framework import status as http_status

from core.utils.models import IdempotencyKey
from core.utils import enums
from core.file_storage.models import FileProcessingJob
from core.utils.helpers import redis
from core.wallet.models import Wallet


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
                cache_instance = redis.RedisTools(
                    cache_key, ttl=ttl
                )
                cached = cache_instance.cache_value
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
                        and "response_status" in cache_instance.cache_value
                    ):
                        return Response(
                            cached.get("response_body") or {}, 
                            status=cached.get("response_status")
                        )

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
                        cached = {
                            "status": enums.KeyProcessStatus.IN_PROGRESS.value,
                            "request_hash": body_hash,
                            "lock_until": locked_until.timestamp(),
                        }
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
                            cached = {
                                "status": enums.KeyProcessStatus.IN_PROGRESS.value,
                                "request_hash": record.request_hash,
                                "lock_until": record.locked_until.timestamp() if record.locked_until else now.timestamp(),
                            }
                            return IdempotencyDecorator._return_response("operation is still being processed")

                        if (
                            record.status in (
                                enums.KeyProcessStatus.SUCCEEDED.value, enums.KeyProcessStatus.FAILED.value
                            )
                            and record.response_status
                        ):
                            # Populate cache and return cached response
                            cached = {
                                "status": record.status,
                                "request_hash": record.request_hash,
                                "response_status": record.response_status,
                                "response_body": record.response_body,
                                "lock_until": now.timestamp(),
                            }
                            return Response(record.response_body or {}, status=record.response_status)
            
                response: Response = function(self, request, *args, **kwargs)

                # Persist result to DB, then cache it
                try:
                    with transaction.atomic():
                        idem_key = IdempotencyKey.objects.select_for_update().get(pk=record.pk)
                        IdempotencyDecorator._persist_db(idem_key, response, now=now, expires_at=expires_at)
                finally:
                    cached = {
                        "status": (
                            enums.KeyProcessStatus.SUCCEEDED.value if 200 <= response.status_code < 300 
                            else enums.KeyProcessStatus.FAILED.value
                        ),
                        "request_hash": body_hash,
                        "response_status": response.status_code,
                        "response_body": getattr(response, "data", None),
                        "lock_until": now.timestamp()
                    }

                return response
            
            function_to_execute.__name__ = function.__name__
            return function_to_execute
        return inner
    

class UpdateObjectStatusDecorator:
    """
    Decorator to wrap background processes that require their statuses updated on failure or success.
    Usage:
      @WebhookDecorator.file_processing(
          client_exceptions=(ValidationError,),
          server_exceptions=(requests.RequestException, Exception),
      )
      def step(...):
          ...
    """

    @staticmethod
    def _bind_view_args(function, self_obj, args, kwargs) -> dict:
        sig = inspect.signature(function)
        bound = sig.bind_partial(self_obj, *args, **kwargs)
        bound.apply_defaults()
        return dict(bound.arguments)
    
    @staticmethod
    def _perform_job_update_func():

        def _cache_job_data(job):
            cache_key = f"POLL_OBJECT_CACHE_{job.id}"
            cache_instance = redis.RedisTools(
                cache_key, ttl=settings.POLL_CACHE_TTL
            )
            cache_instance.cache_value = {
                "status": job.status,
                "owner": job.owner.id,
                "file": {
                    "file_id": job.file.id,
                    "file_name": job.file.original_filename,
                    "file_purpose": job.file.file_purpose,
                    "file_key": job.file.file_key,
                }
            } 

        def success(args):
            job = (FileProcessingJob.objects.select_related("file")
                   .only(
                       "id", "status", 
                       "owner_id", 
                       "file__id", "file__original_filename", "file__file_purpose", "file__file_key",
                    )
                   .filter(id=args["job_id"]).first()
                )
            if job.status != enums.JobStatus.COMPLETED.value:
                job.mark_completed()  
                _cache_job_data(job)  
            
        
        def client_error(exc, args):
            job = (FileProcessingJob.objects.select_related("file")
                   .only(
                       "id", "status", 
                       "owner_id", 
                       "file__id", "file__original_filename", "file__file_purpose", "file__file_key",
                    )
                   .filter(id=args["job_id"]).first()
                )
            if job.status != enums.JobStatus.FAILED.value:
                job.mark_failed(f"{str(exc)}")
                _cache_job_data(job)  

        
        def server_error(args):
            job = (FileProcessingJob.objects.select_related("file")
                   .only(
                       "id", "status", 
                       "owner_id", 
                       "file__id", "file__original_filename", "file__file_purpose", "file__file_key",
                    )
                   .filter(id=args["job_id"]).first()
                )
            if job.status != enums.JobStatus.FAILED.value:
                job.mark_failed("an internal server error occured.")
                _cache_job_data(job)  
    
        return success, client_error, server_error
    

    @staticmethod
    def _perform_wallet_update_func():
        def _cache_wallet_data(wallet):
            cache_key = f"POLL_OBJECT_CACHE_{wallet.pk}"
            cache_instance = redis.RedisTools(
                cache_key, ttl=settings.POLL_CACHE_TTL
            )
            cache_instance.cache_value = {
                "status": wallet.creation_status,
                "owner": wallet.owner.id,
                "wallet": {
                    "account_reference": wallet.pk,
                    "barter_id": wallet.barter_id,
                }
            } 

        def success(args):
            wallet = (Wallet.objects.only(
                       "pk", "owner_id",
                       "creation_status", "barter_id",
                    )
                   .filter(id=args["wallet_pk"]).first()
                )
            if wallet.creation_status != enums.WalletCreationStatus.COMPLETED.value:
                wallet.creation_status = enums.WalletCreationStatus.COMPLETED.value
                wallet.save(update_fields=["creation_status"])
                _cache_wallet_data(wallet)  
            
        
        def client_error(exc, args):
            wallet = (Wallet.objects.only(
                       "pk", "owner_id",
                       "creation_status", "barter_id",
                    )
                   .filter(id=args["wallet_pk"]).first()
                )
            if wallet.creation_status != enums.WalletCreationStatus.FAILED.value:
                wallet.creation_status = enums.WalletCreationStatus.FAILED.value
                wallet.save(update_fields=["creation_status"])
                _cache_wallet_data(wallet)  
        
        
        def server_error(args):
            wallet = (Wallet.objects.only(
                       "pk", "owner_id",
                       "creation_status", "barter_id",
                    )
                   .filter(id=args["wallet_pk"]).first()
                )
            if wallet.creation_status != enums.WalletCreationStatus.FAILED.value:
                wallet.creation_status = enums.WalletCreationStatus.FAILED.value
                wallet.save(update_fields=["creation_status"])
                _cache_wallet_data(wallet)  
        
        return success, client_error, server_error
    

    @staticmethod
    def _perform_virtual_account_update_func():

        def _cache_wallet_data(wallet, status: str):
            cache_key = f"POLL_OBJECT_CACHE_{wallet.pk}"
            cache_instance = redis.RedisTools(
                cache_key, ttl=settings.POLL_CACHE_TTL
            )
            cache_instance.cache_value = {
                "status": status,
                "owner": wallet.owner.id,
                "wallet": {
                    "virtual_bank_name": wallet.virtual_bank_name,
                    "virtual_bank_code": wallet.virtual_bank_code,
                    "virtual_account_number": wallet.virtual_account_number
                }
            } 

        def success(args):
            wallet = (Wallet.objects.only(
                       "pk", "owner_id",
                       "virtual_account_number", "virtual_bank_name", 
                       "virtual_bank_code"
                    )
                   .filter(id=args["wallet_pk"]).first()
                )
            _cache_wallet_data(wallet, status="fetched")
        
        def client_error(exc, args):
            wallet = (Wallet.objects.only(
                       "pk", "owner_id",
                       "virtual_account_number", "virtual_bank_name", 
                       "virtual_bank_code"
                    )
                   .filter(id=args["wallet_pk"]).first()
                )
            _cache_wallet_data(wallet, status="failed")


        def server_error(args):
            wallet = (Wallet.objects.only(
                       "pk", "owner_id",
                       "virtual_account_number", "virtual_bank_name", 
                       "virtual_bank_code"
                    )
                   .filter(id=args["wallet_pk"]).first()
                )
            _cache_wallet_data(wallet, status="fetched")  
        
        return success, client_error, server_error


    @staticmethod
    def _wrap(
        on_success: bool,
        perform_update_func: Callable,
        server_exceptions: tuple[type[BaseException], ...],   
        client_exceptions: tuple[type[BaseException], ...]=ValueError,        
    ):
        def inner(function):
            def function_to_execute(self, *args, **kwargs):
                context = kwargs.setdefault("context", {})
                bound = UpdateObjectStatusDecorator._bind_view_args(
                    function, self, args, kwargs
                )
                # build arguments for payload builders
                bind_args = {
                    "job_id": bound.get("job_id") or None,
                    "user_id": bound.get("user_id") or None,
                    "wallet_pk": bound.get("wallet_pk") or None
                }
                success, client_error, server_error = perform_update_func()
                try:
                    response = function(self, *args, **kwargs)
                except client_exceptions as exc: 
                    if bind_args["wallet_pk"] is None:
                        bind_args["wallet_pk"] = kwargs["context"].get("wallet_pk", None)
                    client_error(exc, bind_args)
                    raise
                except server_exceptions as exc:
                    if bind_args["wallet_pk"] is None:
                        bind_args["wallet_pk"] = kwargs["context"].get("wallet_pk", None)
                    server_error(bind_args)
                    raise
                else:
                    if on_success:
                        if bind_args["wallet_pk"] is None:
                            bind_args["wallet_pk"] = kwargs["context"].get("wallet_pk", None) 
                        success(bind_args)
                    return response
            function_to_execute.__name__ = function.__name__
            return function_to_execute
        return inner


    @staticmethod
    def file_processing(
        *,
        on_success: bool = False,
        server_exceptions: tuple[type[BaseException], ...],
        client_exceptions: tuple[type[BaseException], ...]=ValueError
    ):
        return UpdateObjectStatusDecorator._wrap(
            on_success=on_success,
            perform_update_func=UpdateObjectStatusDecorator._perform_job_update_func,
            server_exceptions=server_exceptions,
            client_exceptions=client_exceptions
        )
    

    @staticmethod
    def wallet_creation(
        *,
        on_success: bool = True,
        server_exceptions: tuple[type[BaseException], ...],
        client_exceptions: tuple[type[BaseException], ...]=ValueError
    ):
        return UpdateObjectStatusDecorator._wrap(
            on_success=on_success,
            perform_update_func=UpdateObjectStatusDecorator._perform_wallet_update_func,
            server_exceptions=server_exceptions,
            client_exceptions=client_exceptions
        )
    

    @staticmethod
    def virtual_account_fetch(
        *,
        on_success: bool = True,
        server_exceptions: tuple[type[BaseException], ...],
        client_exceptions: tuple[type[BaseException], ...]=ValueError
    ):
        return UpdateObjectStatusDecorator._wrap(
            on_success=on_success,
            perform_update_func=UpdateObjectStatusDecorator._perform_virtual_account_update_func,
            server_exceptions=server_exceptions,
            client_exceptions=client_exceptions
        )

    # @staticmethod
    # def bank_charge(
    #     *,
    #     fail_event: str = enums.WebhookEvent.BANK_CHARGE_INITIATION_FAILED.value,
    #     server_exceptions: tuple[type[BaseException], ...],
    #     success_event: str = enums.WebhookEvent.BANK_CHARGE_INITIATED.value,
    #     client_exceptions: tuple[type[BaseException], ...]=ValueError
    # ):
    #     return WebhookTriggerDecorator._wrap(
    #         fail_event=fail_event,
    #         server_exceptions=server_exceptions,
    #         payload_builder=WebhookTriggerDecorator._build_bank_charge_payload,
    #         success_event=success_event,
    #         client_exceptions=client_exceptions
    #     )