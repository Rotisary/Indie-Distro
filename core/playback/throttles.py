from rest_framework.throttling import UserRateThrottle


class RetrievePlaybackThrottle(UserRateThrottle):
    scope = "playback_retrieve"


class RefreshPlaybackThrottle(UserRateThrottle):
    scope = "playback_refresh"
