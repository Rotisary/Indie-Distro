from django.urls import reverse

import pytest
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.test import APIClient

from core.file_storage import views as file_storage_views
from core.file_storage.models import FileModel, FileProcessingJob
from core.utils import enums

pytestmark = pytest.mark.django_db

GET_SIGNED_URL = reverse("get-signed-url")
CREATE_FILE_OBJECT_URL = reverse("create-file-object")


def retrieve_file_url(file_id):
    return reverse("retrieve-file", args=[file_id])


def delete_file_url(file_id):
    return reverse("delete-file", args=[file_id])


def build_signed_url_payload(**overrides):
    payload = {
        "file_name": "video.mp4",
        "purpose": enums.FilePurposeType.MAIN_FILE.value,
    }
    payload.update(overrides)
    return payload


def build_create_file_payload(file_id, **overrides):
    payload = {
        "id": file_id,
        "file_purpose": enums.FilePurposeType.MAIN_FILE.value,
        "original_filename": "video.mp4",
    }
    payload.update(overrides)
    return payload


def patch_file_cache(monkeypatch, cached_value):
    monkeypatch.setattr(file_storage_views.cache, "get", lambda key: cached_value)
    monkeypatch.setattr(file_storage_views.cache, "delete", lambda key: None)


# Get signed upload URL


def test_get_signed_url_success(authenticated_client, monkeypatch):
    monkeypatch.setattr(
        file_storage_views.FileUploadUtils,
        "get_file_key",
        lambda *args, **kwargs: {
            "file_id": "file-123",
            "file_key": "uploads/user/main/file-123.mp4",
        },
    )
    monkeypatch.setattr(
        file_storage_views.FileUploadUtils,
        "generate_presigned_upload_url",
        lambda *args, **kwargs: "https://example.com/upload",
    )

    response = authenticated_client.post(
        GET_SIGNED_URL, build_signed_url_payload(), format="json"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["file_id"] == "file-123"
    assert response.data["signed_url"] == "https://example.com/upload"


def test_get_signed_url_unauthorized(anonymous_client):
    response = anonymous_client.post(
        GET_SIGNED_URL, build_signed_url_payload(), format="json"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_signed_url_forbidden(monkeypatch, user):
    monkeypatch.setattr(
        file_storage_views.GetSignedUploadURL, "permission_classes", [IsAdminUser]
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(GET_SIGNED_URL, build_signed_url_payload(), format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_get_signed_url_invalid_payload(authenticated_client):
    response = authenticated_client.post(
        GET_SIGNED_URL,
        build_signed_url_payload(purpose="not-a-purpose"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_get_signed_url_missing_required_fields(authenticated_client):
    response = authenticated_client.post(GET_SIGNED_URL, {}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_get_signed_url_not_found(anonymous_client):
    response = anonymous_client.post(
        "/api/files/get_signed_url/unknown/",
        build_signed_url_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# Create file object


def test_create_file_object_success(authenticated_client, user, monkeypatch):
    file_id = "upload-file-1"
    cached_metadata = {"file_key": "uploads/test.mp4", "owner": user.id}

    patch_file_cache(monkeypatch, cached_metadata)
    monkeypatch.setattr(file_storage_views.start_pipeline, "delay", lambda *_: None)

    response = authenticated_client.post(
        CREATE_FILE_OBJECT_URL,
        build_create_file_payload(file_id),
        format="json",
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert FileModel.objects.filter(id=file_id).exists()
    assert FileProcessingJob.objects.filter(file_id=file_id, owner=user).exists()


def test_create_file_object_unauthorized(anonymous_client):
    response = anonymous_client.post(
        CREATE_FILE_OBJECT_URL,
        build_create_file_payload("upload-file-2"),
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_file_object_forbidden(
    authenticated_client, other_creator_user, monkeypatch
):
    cached_metadata = {"file_key": "uploads/test.mp4", "owner": other_creator_user.id}

    patch_file_cache(monkeypatch, cached_metadata)

    response = authenticated_client.post(
        CREATE_FILE_OBJECT_URL,
        build_create_file_payload("upload-file-3"),
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_file_object_invalid_payload(authenticated_client):
    response = authenticated_client.post(
        CREATE_FILE_OBJECT_URL,
        build_create_file_payload("upload-file-4", file_purpose="invalid"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_create_file_object_missing_required_fields(authenticated_client):
    response = authenticated_client.post(CREATE_FILE_OBJECT_URL, {}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_create_file_object_not_found(anonymous_client):
    response = anonymous_client.post(
        "/api/files/create_file_object/unknown/",
        build_create_file_payload("upload-file-5"),
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# Retrieve file


def test_retrieve_file_success(creator_client, file_model):
    response = creator_client.get(retrieve_file_url(file_model.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == file_model.id


def test_retrieve_file_unauthorized(anonymous_client, file_model):
    response = anonymous_client.get(retrieve_file_url(file_model.id))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_retrieve_file_forbidden(authenticated_client, file_model):
    response = authenticated_client.get(retrieve_file_url(file_model.id))

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_retrieve_file_not_found(creator_client):
    response = creator_client.get(retrieve_file_url("missing-file"))

    assert response.status_code == status.HTTP_404_NOT_FOUND


# Delete file


def test_delete_file_success(creator_client, file_model):
    response = creator_client.delete(delete_file_url(file_model.id))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not FileModel.objects.filter(id=file_model.id).exists()


def test_delete_file_unauthorized(anonymous_client, file_model):
    response = anonymous_client.delete(delete_file_url(file_model.id))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_delete_file_forbidden(creator_client, released_short):
    response = creator_client.delete(delete_file_url(released_short.file.id))

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert FileModel.objects.filter(id=released_short.file.id).exists()


def test_delete_file_not_found(creator_client):
    response = creator_client.delete(delete_file_url("missing-file"))

    assert response.status_code == status.HTTP_404_NOT_FOUND
