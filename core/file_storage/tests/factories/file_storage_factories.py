import factory

from core.file_storage.models import FileModel
from core.users.tests.factories.user_factories import UserFactory
from core.utils import enums


class FileModelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FileModel

    id = factory.Sequence(lambda n: f"file-{n}")
    owner = factory.SubFactory(UserFactory)
    file_purpose = enums.FilePurposeType.MAIN_FILE.value
    file_key = factory.Sequence(lambda n: f"file-key-{n}")
    mime_type = "video/mp4"
    original_filename = "video.mp4"
    is_verified = True
