from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField
from django.utils.text import slugify


from  core.utils.mixins import BaseModelMixin
from core.utils.enums import FilmGenreType, FilmCategoryType
from core.users.models import User


class Feed(BaseModelMixin):
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="films",
        verbose_name=_("Owned By"),
    )
    title = models.CharField(_("Film Title"), null=False, max_length=225)
    slug = models.SlugField(
        _("Slug"),
        max_length=255,
        blank=True,
        help_text=_("Auto-generated slug"),
    )
    plot = models.TextField(
        _("Film Plot"), null=False, blank=False, help_text=_("A quick plot of the film")
    )
    genre = models.CharField(
        _("Film Genre"),
        choices=FilmGenreType.choices(),
        max_length=100,
        blank=False,
        null=False,
        help_text=_("The genre that the film falls under")
    )
    type = models.CharField(
        _("Film Type"),
        choices=FilmCategoryType.choices(),
        max_length=100,
        blank=False,
        null=False,
        help_text=_("The type of film e.g Series, Standalone")
    )
    length = models.TimeField(_("Film Length"), null=False, blank=True)
    cast = ArrayField(
        models.CharField(max_length=100),
        verbose_name=_("Film Actors"),
        blank=False,
        null=False,
        help_text=_("List of the names of major actors from the film"),
        default=list,
    )
    crew = ArrayField(
        models.CharField(max_length=100),
        verbose_name=_("Film Crew"),
        blank=True,
        null=True,
        help_text=_("List of the names of film crew members"),
        default=list,
    )
    language = models.CharField(
        _("Language"),
        max_length=2,
        default="en",
        help_text="Language of the movie, e.g., 'en' for English",
    )
    saved = models.ManyToManyField(
        to="users.User",
        verbose_name=_("Users Who Have Bookmarked the film"),
        related_name="bookmarked_films",
        blank=True,
    )


    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
        

    class Meta:
        verbose_name = _("Film")
        verbose_name_plural = _("Films")


    def __str__(self):
        return f"{self.slug}"
