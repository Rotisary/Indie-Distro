from core.utils import enums
from core.file_storage.models import FileProcessingJob

class CreateWebhookEventPayload:

    @staticmethod
    def job_processing_completed(job_id) -> dict:
        job = FileProcessingJob.objects.get(id=job_id)
        payload = {
            "status": enums.JobStatus.COMPLETED.value,
            "owner": job.owner.id,
            "file": {
                "file_id": job.file.id,
                "file_name": job.file.original_filename,
                "file_purpose": job.file.file_purpose,
                "file_key": job.file.file_key,
            },
            "media": {
                "media_obj_id": job.file.film.id if job.file.film else (job.file.short.id if job.file.short else None),
                "media_type": "film" if job.file.film else "short",
            }
        }
        return payload


    @staticmethod
    def job_processing_failed(job_id, error_message: str, kind: str) -> dict:
        job = FileProcessingJob.objects.get(id=job_id)
        payload = {
            "status": enums.JobStatus.FAILED.value,
            "owner": job.owner.id,
            "file": {
                "file_id": job.file.id,
                "file_name": job.file.original_filename,
                "file_purpose": job.file.file_purpose,
                "file_key": job.file.file_key,
            },
            "kind": kind,
            "error_message": error_message
        }
        return payload


    @staticmethod
    def wallet_creation_completed(user_id, data: dict) -> dict:
        payload={
            "user_id": user_id,
            "wallet_account_reference": data['account_reference'],
            "wallet_barter_id": data['barter_id'],
        }  
        return payload  


    @staticmethod
    def wallet_creation_failed(user_id, error_message: str, kind: str) -> dict:
        payload={
            "user_id": user_id,
            "kind": kind,
            "error_message": error_message
        }  
        return payload  