import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField
from django.db.models import JSONField
from django.utils.text import slugify


from  core.utils.mixins import BaseModelMixin
from core.utils.enums import (
    FilmGenreType, 
    FilmCategoryType,
    FilmSaleType,
    PurchaseStatusType
)
from core.users.models import User
from core.file_storage.models import FileModel


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
    length = models.DurationField(_("Film Length(Runtime)"), null=True, blank=True)
    release_date = models.DateField(
        _("Release Date "),
        null=True,
        blank=True,
        help_text=_("The date the film was/is to be released")
    )
    is_released = models.BooleanField(
        _("Has the movie been released?"),
        blank=True,
        null=True,
        default=False
    )
    cast = ArrayField(
        models.CharField(max_length=100),
        verbose_name=_("Film Actors"),
        blank=False,
        null=False,
        help_text=_("List of the names of major actors from the film"),
        default=list,
    )
    crew = JSONField(
        verbose_name=_("Film Crew"),
        blank=True,
        null=True,
        help_text=_("List of the names of film crew members"),
        default=dict,
    )
    language = models.CharField(
        _("Language"),
        max_length=2,
        default="en",
        help_text="Language of the movie, e.g., 'en' for English",
    )
    sale_type = models.CharField(
        choices=FilmSaleType.choices(), 
        default=FilmSaleType.ONE_TIME_SALE.value,
        verbose_name=_("Sale Type"),
        blank=True,
        help_text=_("The sale type of the film,(one time sale, rental)"),     
    )
    price = models.DecimalField(
        _("Film price"),
        decimal_places=2, 
        max_digits=17,
        null=True, 
        blank=True
    )
    rental_duration = models.IntegerField(
        verbose_name=_("Rental Duration(in hours)"), blank=True, null=True
    )
    film_file = models.ForeignKey(
        to=FileModel,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name=_("The File of the Film")
    )
    bought = models.ManyToManyField(
        to="users.User",
        through="Purchase",
        verbose_name=_("Users Who Have Paid for the film"),
        related_name="bought_films",
        blank=True
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
    

class Purchase(BaseModelMixin):
    id = models.CharField(
        primary_key=True, 
        blank=True, 
        null=False, 
        unique=True, 
        max_length=100
    )
    owner = models.ForeignKey(
        to="users.User",
        verbose_name=_("Purchase Owner"),
        null=False,
        blank=False,
        related_name="purchases_made",
        on_delete=models.DO_NOTHING,
        help_text=_("User that made purchase"),
    )
    film = models.ForeignKey(
        to=Feed,
        verbose_name="Film of Purchase",
        on_delete=models.CASCADE,
        related_name="purchases",
        help_text=_("the film that the purchase was made for")
    )
    status = models.CharField(
        choices=PurchaseStatusType.choices(), 
        default=PurchaseStatusType.REVOKED.value, 
        verbose_name=_("The current status of the purchase")
    )
    expiry_time = models.TimeField(
        _("Time of Expiry"), 
        blank=True, 
        null=True,
        help_text=_("film time of expiry for rented films")
    )

    class Meta:
        verbose_name = _('Film Purchase')
        verbose_name_plural = _("Film Purchases")


    def save(self, *args, **kwargs):
        if not self.id:
            self.id = uuid.uuid4()
        super().save(*args, **kwargs)

    
    def __str__(self):
        return f"film({self.film.id})-{self.owner.first_name}-purchase({self.id})"

