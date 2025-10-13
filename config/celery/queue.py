from kombu import Queue


class CeleryQueue:
    class Definitions:
        BEATS = "beats"
        EMAIL_AND_NOTIFICATION = "email-notification"
        PACKAGING = "packaging"
        TRANSCODING = "transcoding"

    @staticmethod
    def queues():
        return tuple(
            (Queue(getattr(CeleryQueue.Definitions, item)))
            for item in filter(
                lambda ref: not ref.startswith("_"), dir(CeleryQueue.Definitions)
            )
        )