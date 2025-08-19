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
