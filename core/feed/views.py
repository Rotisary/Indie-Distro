from rest_framework import status, response, views, filters, generics
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db import transaction as db_transaction
from django.apps import apps

from loguru import logger
from drf_spectacular.utils import extend_schema
from django_filters.rest_framework import DjangoFilterBackend


from .models import Feed, Short, Purchase
from .filters import FilmFilter, ShortFilter
from .serializers import FeedSerializer, ShortSerializer, FilmPurchaseSerializer
from core.utils import mixins as global_mixins, exceptions
from core.utils.helpers.decorators import (
    RequestDataManipulationsDecorators, 
    IdempotencyDecorator
)
from core.utils.helpers import payment
from core.utils.commons.utils import serializers
from core.utils.permissions import (
    IsAccountType, 
    IsFilmOwner, 
    IsShortOwner,
    FilmNotReleased
)
from core.utils import enums


@extend_schema(tags=["feed"])
class ListCreateFeed(views.APIView):
    http_method_names = ["post", "get"]
    parser_classes = [JSONParser, ]
    permission_classes = [IsAuthenticated, IsAccountType.IsCreatorAccount, ]


    @extend_schema(
        description="endpoint for adding a new film",
        request=FeedSerializer.FeedCreate,
        responses={201: FeedSerializer.FeedRetrieve}, 
    )
    @RequestDataManipulationsDecorators.update_request_data_with_owner_data("owner")
    def post(self, request):
        serializer = FeedSerializer.FeedCreate(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        logger.success(f"Film created with title: {instance.title}")
        serializer = FeedSerializer.FeedRetrieve(instance=instance)
        return response.Response(data=serializer.data, status=status.HTTP_201_CREATED)

    
    @extend_schema(
        description="endpoint for retrieving list of films owned by the authenticated user",
        request=None,
        responses={200: FeedSerializer.FeedRetrieve(many=True)}, 
    )
    def get(self, request):
        queryset = Feed.objects.filter(owner=request.user)
        serializer = FeedSerializer.FeedRetrieve(queryset, many=True)
        # logger.info(f"Retrieved {len(serializer.data['results'])} films for the user.")
        return response.Response(data=serializer.data, status=status.HTTP_200_OK)
    
@extend_schema(tags=["feed"])
class RetrieveUpdateDeleteFeed(views.APIView):
    http_method_names = ["get", "patch", "delete"]
    permission_classes = [
        IsAuthenticated, 
        IsAccountType.IsCreatorAccount, 
        IsFilmOwner, 
        FilmNotReleased
    ]
    parser_classes = [JSONParser, ]


    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated(), ]
        if self.request.method == "DELETE":
            return [
                IsAuthenticated(), 
                IsAccountType.IsCreatorAccount(), 
                IsFilmOwner(), 
            ]
        
        return super().get_permissions()


    @extend_schema(
        description="endpoint for retrieving details of a specific film",
        request=None,
        responses={200: FeedSerializer.FeedRetrieve},
    )
    def get(self, request, pk):
        try: 
            feed = Feed.objects.get(id=pk)          
            serializer = FeedSerializer.FeedRetrieve(instance=feed)
            logger.info(f"Retrieved film with ID: {pk}")
            return response.Response(data=serializer.data, status=status.HTTP_200_OK)
        except Feed.DoesNotExist:
            raise exceptions.CustomException(
                "Film not found", 
                status_code=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        description="endpoint for updating details of a specific film",
        request=FeedSerializer.FeedCreate,
        responses={200: FeedSerializer.FeedRetrieve},
    )
    @RequestDataManipulationsDecorators.update_request_data_with_owner_data("owner")
    def patch(self, request, pk):
        try:
            feed = Feed.objects.get(id=pk, owner=request.user)
            self.check_object_permissions(request, feed)
            serializer = FeedSerializer.FeedCreate(instance=feed, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            logger.success(f"Film with ID: {pk} successfully updated.")
            serializer = FeedSerializer.FeedRetrieve(instance=instance)
            return response.Response(data=serializer.data, status=status.HTTP_200_OK)
        except Feed.DoesNotExist:
            raise exceptions.CustomException(
                "Film not found", 
                status_code=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        description="Delete a specific film",
        request=None,
        responses={204: None},
    )
    def delete(self, request, pk):
        try:
            feed = Feed.objects.get(id=pk, owner=request.user)
            self.check_object_permissions(request, feed)
            feed.delete()
            logger.success(f"Film with ID: {pk} deleted.")
            return response.Response(status=status.HTTP_204_NO_CONTENT)
        except Feed.DoesNotExist:
            raise exceptions.CustomException(
                "Film not found", status_code=status.HTTP_404_NOT_FOUND
            )


@extend_schema(tags=["feed"])
class PublicFeedList(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = FeedSerializer.FeedRetrieve
    queryset = Feed.objects.filter(is_released=True)
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = FilmFilter
    ordering_fields = ["release_date", "price"]
    ordering = ["-release_date"]


@extend_schema(tags=["shorts"])
class ListCreateShort(views.APIView):
    http_method_names = ["post", "get"]
    parser_classes = [JSONParser]
    permission_classes = [IsAuthenticated, IsAccountType.IsCreatorAccount]

    @extend_schema(
        description="Create a new short",
        request=ShortSerializer.ShortCreate,
        responses={201: ShortSerializer.ShortRetrieve},
    )
    @RequestDataManipulationsDecorators.update_request_data_with_owner_data("owner")
    def post(self, request):
        serializer = ShortSerializer.ShortCreate(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        logger.success(f"Short created with title: {instance.title}")
        serializer = ShortSerializer.ShortRetrieve(instance=instance)
        return response.Response(data=serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        description="List shorts owned by the authenticated creator",
        request=None,
        responses={200: ShortSerializer.ShortRetrieve(many=True)},
    )
    def get(self, request):
        queryset = Short.objects.filter(owner=request.user)
        serializer = ShortSerializer.ShortRetrieve(queryset, many=True)
        return response.Response(data=serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["shorts"])
class RetrieveUpdateDeleteShort(views.APIView):
    http_method_names = ["get", "patch", "delete"]
    parser_classes = [JSONParser]
    permission_classes = [
        IsAuthenticated, 
        IsAccountType.IsCreatorAccount, 
        IsShortOwner
    ]

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        if self.request.method == "DELETE":
            return [
                IsAuthenticated(), 
                IsAccountType.IsCreatorAccount(), 
                IsShortOwner(), 
            ]
        return super().get_permissions()

    @extend_schema(
        description="Retrieve details of a specific short by ID",
        request=None,
        responses={200: ShortSerializer.ShortRetrieve},
    )
    def get(self, request, pk):
        try:
            short = Short.objects.get(id=pk)
            serializer = ShortSerializer.ShortRetrieve(instance=short)
            logger.info(f"Retrieved short with ID: {pk}")
            return response.Response(data=serializer.data, status=status.HTTP_200_OK)
        except Short.DoesNotExist:
            raise exceptions.CustomException(
                "Short not found", status_code=status.HTTP_404_NOT_FOUND
            )

    @extend_schema(
        description="Update an existing short",
        request=ShortSerializer.ShortCreate,
        responses={200: ShortSerializer.ShortRetrieve},
    )
    @RequestDataManipulationsDecorators.update_request_data_with_owner_data("owner")
    def patch(self, request, pk):
        try:
            short = Short.objects.get(id=pk, owner=request.user)
            self.check_object_permissions(request, short)
            serializer = ShortSerializer.ShortCreate(
                instance=short, data=request.data, partial=True, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            logger.success(f"Short with ID: {pk} successfully updated.")
            serializer = ShortSerializer.ShortRetrieve(instance=instance)
            return response.Response(data=serializer.data, status=status.HTTP_200_OK)
        except Short.DoesNotExist:
            raise exceptions.CustomException(
                "Short not found", status_code=status.HTTP_404_NOT_FOUND
            )

    @extend_schema(
        description="Delete a specific short",
        request=None,
        responses={204: None},
    )
    def delete(self, request, pk):
        try:
            short = Short.objects.get(id=pk, owner=request.user)
            self.check_object_permissions(request, short)
            short.delete()
            logger.success(f"Short with ID: {pk} deleted.")
            return response.Response(status=status.HTTP_204_NO_CONTENT)
        except Short.DoesNotExist:
            raise exceptions.CustomException(
                "Short not found", status_code=status.HTTP_404_NOT_FOUND
            )


@extend_schema(tags=["shorts"])
class PublicShortsList(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ShortSerializer.ShortRetrieve
    queryset = Short.objects.filter(is_released=False)
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ShortFilter
    ordering_fields = [
        "release_date", 
        "views_count",
        "likes_count",
        "comments_count"
    ]
    ordering = ["-release_date"]


@extend_schema(tags=["purchases"])
class PurchaseFilm(views.APIView):
    http_method_names = ["post"]
    parser_classes = [JSONParser]
    permission_classes = [IsAuthenticated, ]   

    @extend_schema(
        description="Endpoint for users to purchase a film",
        request=FilmPurchaseSerializer.CreatePurchase,
        responses={200: FilmPurchaseSerializer.FilmPurchaseResponse},
    )
    @IdempotencyDecorator.make_endpoint_idempotent(ttl=300)
    def post(self, request, pk=None):
        film = Feed.objects.get(id=pk)
        user = request.user
        entry_lines = [
            {
                "user": user,
                "account_type": enums.LedgerAccountType.EXTERNAL_PAYMENT.value,
                "entry_type": enums.EntryType.DEBIT,
                "amount": film.price
            },
            {
                "user": film.owner,
                "account_type": enums.LedgerAccountType.PROVIDER_WALLET.value,
                "entry_type": enums.EntryType.CREDIT,
                "amount": film.price
            }
        ]
        with db_transaction.atomic():
            transaction = payment.PostLedgerData.as_pending(
                ledger_data=entry_lines,
                description="film purchase via bank charge"
            )

            serializer = FilmPurchaseSerializer.CreatePurchase(
                data=request.data,
                context={
                    "request": request, 
                    "film": film,
                    "transaction": transaction
                },
            )
            serializer.is_valid(raise_exception=True)
            purchase = serializer.save()

        if serializer.validated_data["method"] == enums.PaymentType.BANK_CHARGE.value:
            payment_helper = payment.PaymentHelper(
                user=user, 
                transaction=transaction,
                amount=film.price,
                payment_type=enums.PaymentType.BANK_CHARGE.value, 
                charge_type="nigerian"
            )
            payment_response = payment_helper.charge_bank()
        else:
            payment_helper = payment.PaymentHelper(
                user=film.owner, 
                transaction=transaction,
                amount=film.price,
                payment_type=enums.PaymentType.TRANSFER.value, 
            )
            beneficiary = {
                "account_number": film.owner.wallet.barter_id,
                "name": f"{film.owner.first_name} {film.owner.last_name}",
            }
            payment_response = payment_helper.transfer(
                beneficiary=beneficiary,
                description="Film purchase via transfer",
                debit_subaccount=film.owner.wallet.account_reference,
            )
        
        status_code = None
        if payment_response.status == "initiated":
            status_code = status.HTTP_202_ACCEPTED
        else:
            status_code = status.HTTP_502_BAD_GATEWAY

        return response.Response(data=payment_response, status=status_code)
        

def _get_model_by_name(name: str):
    matches = [m for m in apps.get_models() if m.__name__.lower() == name.lower()]
    if not matches:
        raise LookupError(f"No model named '{name}' found.")
    if len(matches) > 1:
        labels = [f"{m._meta.app_label}.{m.__name__}" for m in matches]
        raise LookupError(f"Ambiguous model name '{name}'. Candidates: {', '.join(labels)}")
    return matches[0]      


@extend_schema(tags=["feed"])
class Bookmark(views.APIView):
    """
    This is the endpoint to bookmark any any object that can be bookmarked.
    The model name and id of the object to be bookmarked must be provided.
    The model must have a 'saved' ManyToManyField to the User model.
    """
    http_method_names = ["post", ]
    parser_classes = [JSONParser, ]


    @extend_schema(
        description="endpoint to bookmark an object",
        request=serializers.Bookmark,
        responses={201: None}
    )
    def post(self, request):
        serializer = serializers.Bookmark(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        model_name = serializer.validated_data["model_name"]
        model = _get_model_by_name(model_name)
        try:
            object = model.objects.get(id=serializer.validated_data["id"])
            response_data = {}
            if request.user not in object.saved.all():
                object.saved.add(request.user)
                response_data["status"] = "success"
            else:
                response_data["status"] = "failed"
            
            return response.Response(
                data=response_data, status=status.HTTP_200_OK
            )
        except model.DoesNotExist:
            raise exceptions.CustomException(
                message=f"{model_name} not found", 
                status_code=status.HTTP_404_NOT_FOUND
            )



@extend_schema(tags=["feed"])
class RemoveBookmark(views.APIView):
    """
    This is the endpoint to remove a bookmark from any object that can be bookmarked.
    The model name and id of the object to be un-bookmarked must be provided.
    The model must have a 'saved' ManyToManyField to the User model.
    """
    http_method_names = ["post", ]
    parser_classes = [JSONParser, ]


    @extend_schema(
        description="endpoint to un-bookmark an object",
        request=serializers.Bookmark,
        responses={201: None}
    )
    def post(self, request):
        serializer = serializers.Bookmark(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        model_name = serializer.validated_data["model_name"]
        model = _get_model_by_name(model_name)
        try:
            object = model.objects.get(id=serializer.validated_data["id"])
            response_data = {}
            if request.user in object.saved.all():
                object.saved.remove(request.user)
                response_data["status"] = "success"
            else:
                response_data["status"] = "failed"

            return response.Response(
                data=response_data, status=status.HTTP_200_OK
            )
        except model.DoesNotExist:
            raise exceptions.CustomException(
                message=f"{model_name} not found", 
                status_code=status.HTTP_404_NOT_FOUND
            )
    

    # @extend_schema(
    #     description="List all the purchases made by a user",
    #     request=None,
    #     responses={200: FilmPurchaseSerializer.RetrievePurchase(many=True)},
    # )
    # def get(self, request):
    #     queryset = Purchase.objects.filter(owner=request.user)
    #     serializer = FilmPurchaseSerializer.RetrievePurchase(queryset, many=True)
    #     return response.Response(data=serializer.data, status=status.HTTP_200_OK)