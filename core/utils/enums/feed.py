from .base import BaseEnum


class FilmGenreType(BaseEnum):
    ACTION = "Action"
    DRAMA = "Drama"
    ROMANCE = "Romance"
    HORROR = "Horror"
    SCI_FI = "Sci-Fi"
    FANTASY = "Fantasy"
    THRILLER = "Thriller"
    COMEDY = "Comedy"


class FilmCategoryType(BaseEnum):
    STANDALONE = "standalone"
    SERIES = "series"
    DOCUMENTARY = "documentary"
    SHORT_FILM = "short film"
    FRANCHISE = "franchise"


class FilmSaleType(BaseEnum):
    ONE_TIME_SALE = "one-time sale"
    RENTAL = "rental"


class PurchaseStatusType(BaseEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    CHARGEBACK = "chargeback"


class ShortType(BaseEnum):
    TRAILER = "trailer"
    TEASER = "teaser"
    SNIPPET = "snippet"
