from django.apps import AppConfig


class FeedConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.feed'

    def ready(self):
        # noqa: F401
        from . import signals 
