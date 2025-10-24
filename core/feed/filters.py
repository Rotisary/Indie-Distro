from django_filters.rest_framework import FilterSet, filters
from django.db.models import Q
from core.utils import enums
from .models import Feed, Short

class FilmFilter(FilterSet):
    owner = filters.NumberFilter(field_name="owner__id", label="Filter by owner ID")
    title = filters.CharFilter(
        field_name="title", 
        lookup_expr="icontains", 
        label="Filter by title of the movie(basic search, case-insensitive match)"
    )
    genre = filters.ChoiceFilter(
        label="Filter by genre(Action, Comedy e.t.c)",
        choices=enums.FilmGenreType.choices()
    )
    type = filters.ChoiceFilter(
        label="Filter by film type(Standalone, Series e.t.c)",
        choices=enums.FilmCategoryType.choices()
    )
    language = filters.CharFilter(
        field_name="language",
        label="Filter by the language of the film"
    )
    release_date__gte = filters.DateFilter(
        field_name="release_date",
        lookup_expr="gte",
        label="Return recent releases"
    )
    release_date__lte = filters.DateFilter(
        field_name="release_date",
        lookup_expr="lte",
        label="Return upcoming releases"
    )
    price = filters.NumberFilter(field_name="price")
    price__gte = filters.NumberFilter(field_name="price", lookup_expr="gte")
    price__lte = filters.NumberFilter(field_name="price", lookup_expr="lte")

    class Meta:
        model = Feed
        fields = []


class ShortFilter(FilterSet):
    owner = filters.NumberFilter(field_name="owner__id", label="Filter by owner ID")
    film = filters.NumberFilter(field_name="film__id", label="Filter by associated film ID")
    type = filters.ChoiceFilter(
        label="Filter by short type(Teaser, Snippet e.t.c)",
        choices=enums.ShortType.choices()
    )
    search = filters.CharFilter(
        method="filter_search", 
        label="Search in caption and tags"
    )

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(caption__icontains=value) | Q(tags__icontains=value)
        )

    class Meta:
        model = Short
        fields = []