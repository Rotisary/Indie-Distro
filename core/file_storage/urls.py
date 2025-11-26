from django.urls import path

from .views import (
    GetSignedUploadURL,
    CreateFileObject,
    RetrieveFile,
    JobStatusPollView
)


urlpatterns = [
    path("get_signed_url/", GetSignedUploadURL.as_view(), name="get-signed-url"),
    path("create_file_object/", CreateFileObject.as_view(), name="create-file-object"),
    path("<str:pk>/", RetrieveFile.as_view(), name="retrieve-file"),
    path("<str:pk>/status/", JobStatusPollView.as_view(), name="job-status-poll"),
]