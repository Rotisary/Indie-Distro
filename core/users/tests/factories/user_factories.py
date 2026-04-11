import factory

from core.users.models import User, UserSession
from core.utils import enums

DEFAULT_PASSWORD = "TestPass123!"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    username = factory.Sequence(lambda n: f"user{n}")
    phone_number = None
    is_email_verified = True
    is_phone_number_verified = True
    is_creator = False
    account_type = enums.UserAccountType.USER.value
    is_staff = False
    is_superuser = False
    password = factory.PostGenerationMethodCall("set_password", DEFAULT_PASSWORD)


    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        raw_password = extracted or DEFAULT_PASSWORD
        self.set_password(raw_password)
        if create:
            self.save(update_fields=["password"])



class UserSessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserSession

    user = factory.SubFactory(UserFactory)
    refresh = factory.Sequence(lambda n: f"refresh-{n}")
    access = factory.Sequence(lambda n: f"access-{n}")
    ip_address = "127.0.0.1"
    user_agent = "pytest"
    is_active = True
