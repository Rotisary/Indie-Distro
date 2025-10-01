from celery import shared_task
from core.utils.helpers.file_storage import BaseStorageHelper, FileProcessingUtils


@shared_task
def extract_file_metadata(file_key):
    file = BaseStorageHelper.generate_presigned_get_url(file_key)
    metadata = FileProcessingUtils.extract_metadata(file)
    return metadata