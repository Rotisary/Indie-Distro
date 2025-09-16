from rest_framework import status, decorators, response, views
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache

import mimetypes
from loguru import logger
from drf_spectacular.utils import extend_schema


from .models import FileModel
from .serializers import FileSerializer, SignedURLRequestSerializer
from core.utils import mixins as global_mixins, exceptions
from core.utils.helpers.decorators import RequestDataManipulationsDecorators
from core.utils.helpers.file_storage import FileUploadUtils
from core.utils.permissions import IsAccountType, IsFilmOwner, FilmNotReleased


@extend_schema(tags=["Files"])
class GetSignedUploadURL(views.APIView):
    http_method_names = ["post", ]
    parser_classes = [JSONParser, ]
    renderer_classes = [JSONRenderer, ]


    @extend_schema(
        description="endpoint to get signed url that would be used for S3 upload by the client",
        request=SignedURLRequestSerializer,
        responses={200: None}
    )
    def post(self, request, *args, **kwargs):
        serializer = SignedURLRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file_name = serializer.validated_data["file_name"]
        file_purpose = serializer.validated_data["purpose"]

        file_metadata = FileUploadUtils.get_file_key(request.user, file_name, file_purpose) 
        signed_url = FileUploadUtils.generate_presigned_upload_url(
            file_metadata["file_key"], file_name
        )
        response_data = {
            "file_id": file_metadata["file_id"],
            "signed_url": signed_url
        }
        return response.Response(data=response_data, status=status.HTTP_200_OK)
    

@extend_schema(tags=["Files"])
class CreateFileObject(views.APIView):
    """
        Client makes a call to this endpoint after direct upload to S3 is completed. 
        Client sends file metadata in post data to create File object in server database
    """
    http_method_names = ["post", ]
    parser_classes = [JSONParser, ]
    renderer_classes = [JSONRenderer, ]


    @staticmethod
    def get_mime_type(file_name=None):
        mime_type = ""
        if file_name:
            mime_type, *_ = mimetypes.guess_type(file_name)

        return mime_type

    @RequestDataManipulationsDecorators.update_request_data_with_owner_data("owner")
    @extend_schema(
        description="endpoint to create file object",
        request=FileSerializer.Create,
        responses={202: FileSerializer.ListRetrieve}
    )
    def post(self, request):
        serializer = FileSerializer.Create(data=request.data)
        serializer.is_valid(raise_exception=True)
        file_id = serializer.validated_data["id"]
        file_name = serializer.validated_data.get("original_filename", None)
        cached_metadata = cache.get(f"pending_upload-{file_id}")

        if not cached_metadata:
            raise exceptions.CustomException(
                message="Expired or Invalid file id!",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        if cached_metadata["owner"] != request.user.id:
            raise exceptions.CustomException(
                message="Permssion Denied",
                status_code=status.HTTP_403_FORBIDDEN
            )
        file = serializer.save(
            file_key=cached_metadata["file_key"], 
            mime_type=self.get_mime_type(file_name=file_name)
        )
        cache.delete(f"pending_upload-{file_id}")
        # TODO: call file processing background task
        serializer = FileSerializer.ListRetrieve(
            instance=file
        )
        return response.Response(
            data={
                "message": "file currently being processed",
                "data": serializer.data
            },
            status=status.HTTP_202_ACCEPTED
        )
    

@extend_schema(tags=["Files"])
class RetrieveFile(views.APIView):
    http_method_names = ["get", ]
    permission_classes = [IsAuthenticated, IsAccountType.IsCreatorAccount, ]
    renderer_classes = [JSONRenderer, ]


    @extend_schema(
        description="retrieve a particular File object",
        request=None,
        responses={200: FileSerializer.ListRetrieve}
    )
    def get(self, request, pk):
        try:
            file = FileModel.objects.get(id=pk)
            serializer = FileSerializer.ListRetrieve(instance=file)
            return response.Response(data=serializer.data, status=status.HTTP_200_OK)
        except FileModel.DoesNotExist:
            raise exceptions.CustomException(
                message="file not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

