from rest_framework import status, decorators, response, views
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticated

from loguru import logger
from drf_spectacular.utils import extend_schema


from .models import Feed, Short
from .serializers import FeedSerializer, ShortSerializer
from core.utils import mixins as global_mixins, exceptions
from core.utils.helpers.decorators import RequestDataManipulationsDecorators
from core.utils.permissions import (
    IsAccountType, 
    IsFilmOwner, 
    IsShortOwner,
    FilmNotReleased
)


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
    
    @RequestDataManipulationsDecorators.update_request_data_with_owner_data("owner")
    @extend_schema(
        description="endpoint for updating details of a specific film",
        request=FeedSerializer.FeedCreate,
        responses={200: FeedSerializer.FeedRetrieve},
    )
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
class Bookmark(views.APIView):
    http_method_names = ["post", ]
    parser_classes = [JSONParser, ]


    @extend_schema(
        description="endpoint to bookmark a film",
        request=FeedSerializer.Bookmark,
        responses={201: None}
    )
    def post(self, request):
        serializer = FeedSerializer.Bookmark(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        feed: Feed = serializer.validated_data["id"]
        response_data = {}
        if request.user not in feed.saved.all():
            feed.saved.add(request.user)
            response_data["status"] = "success"
        else:
            response_data["status"] = "failed"

        return response.Response(
            data=response_data, status=status.HTTP_200_OK
        )


@extend_schema(tags=["feed"])
class RemoveBookmark(views.APIView):
    http_method_names = ["post", ]
    parser_classes = [JSONParser, ]
    renderer_classes = [JSONRenderer, ]


    @extend_schema(
        description="endpoint to un-bookmark a film",
        request=FeedSerializer.Bookmark,
        responses={201: None}
    )
    def post(self, request):
        serializer = FeedSerializer.Bookmark(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        feed: Feed = serializer.validated_data["id"]
        response_data = {}
        if request.user in feed.saved.all():
            feed.saved.remove(request.user)
            response_data["status"] = "success"
        else:
            response_data["status"] = "failed"

        return response.Response(
            data=response_data, status=status.HTTP_200_OK
        )


@extend_schema(tags=["shorts"])
class ListCreateShort(views.APIView):
    http_method_names = ["post", "get"]
    parser_classes = [JSONParser]
    permission_classes = [IsAuthenticated, IsAccountType.IsCreatorAccount]

    @extend_schema(
        description="Create a new short",
        request=ShortSerializer.ShortCreate,
        responses={201: ShortSerializer.Retrieve},
    )
    @RequestDataManipulationsDecorators.update_request_data_with_owner_data("owner")
    def post(self, request):
        serializer = ShortSerializer.ShortCreate(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        logger.success(f"Short created with title: {instance.title}")
        serializer = ShortSerializer.Retrieve(instance=instance)
        return response.Response(data=serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        description="List shorts owned by the authenticated creator",
        request=None,
        responses={200: ShortSerializer.Retrieve(many=True)},
    )
    def get(self, request):
        queryset = Short.objects.filter(owner=request.user)
        serializer = ShortSerializer.Retrieve(queryset, many=True)
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
        return super().get_permissions()

    @extend_schema(
        description="Retrieve details of a specific short by ID",
        request=None,
        responses={200: ShortSerializer.Retrieve},
    )
    def get(self, request, pk):
        try:
            short = Short.objects.get(id=pk)
            serializer = ShortSerializer.Retrieve(instance=short)
            logger.info(f"Retrieved short with ID: {pk}")
            return response.Response(data=serializer.data, status=status.HTTP_200_OK)
        except Short.DoesNotExist:
            raise exceptions.CustomException(
                "Short not found", status_code=status.HTTP_404_NOT_FOUND
            )

    @RequestDataManipulationsDecorators.update_request_data_with_owner_data("owner")
    @extend_schema(
        description="Update an existing short",
        request=ShortSerializer.ShortCreate,
        responses={200: ShortSerializer.Retrieve},
    )
    def patch(self, request, pk):
        try:
            short = Short.objects.get(id=pk, owner=request.user)
            self.check_object_permissions(request, short)
            serializer = ShortSerializer.Create(
                instance=short, data=request.data, partial=True, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            logger.success(f"Short with ID: {pk} successfully updated.")
            serializer = ShortSerializer.Retrieve(instance=instance)
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