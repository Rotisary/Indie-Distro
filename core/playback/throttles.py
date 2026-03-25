from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class RetrievePlaybackThrottle(UserRateThrottle):
    scope = "playback_retrieve"


class RefreshPlaybackThrottle(UserRateThrottle):
    scope = "playback_refresh"


class RetrieveShortPlaybackThrottle(AnonRateThrottle):
    scope = "short_playback_retrieve"


class RefreshShortPlaybackThrottle(AnonRateThrottle):
    scope = "short_playback_refresh"
