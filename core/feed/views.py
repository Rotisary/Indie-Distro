from rest_framework import status, decorators, response, views
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema


from .models import Feed
from .serializers import FeedSerializer
from core.utils import mixins as global_mixins, exceptions
from core.utils.helpers.decorators import RequestDataManipulationsDecorators
from core.utils.permissions import IsAccountType


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
        serializer = FeedSerializer.FeedRetrieve(instance=instance)
        return response.Response(data=serializer.data, status=status.HTTP_201_CREATED)

    
    @extend_schema(
        description="endpoint for retrieving list of films owned by the authenticated user",
        responses={200: FeedSerializer.FeedRetrieve}, 
    )
    def get(self, request):
        queryset = Feed.objects.filter(owner=request.user)
        serializer = FeedSerializer.FeedRetrieve(queryset, many=True)
        return response.Response(data=serializer.data, status=status.HTTP_200_OK)
    



