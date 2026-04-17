import factory

from core.users.tests.factories.user_factories import UserFactory
from core.websocket.models import EventLog


class EventLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EventLog

    user = factory.SubFactory(UserFactory)
    type = factory.Sequence(lambda n: f"event-type-{n}")
    entity = "wallet"
    status = "completed"
    resource_id = factory.Sequence(lambda n: f"res-{n}")
    payload = factory.LazyAttribute(
        lambda obj: {"event": obj.type, "status": obj.status}
    )
