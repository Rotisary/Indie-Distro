import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField
from django.db.models import JSONField
from django.utils.text import slugify


from  core.utils.mixins import BaseModelMixin
from core.utils import enums
from core.users.models import User
from core.file_storage.models import FileModel
from core.payment.models import Transaction


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
        choices=enums.FilmGenreType.choices(),
        max_length=100,
        blank=False,
        null=False,
        help_text=_("The genre that the film falls under")
    )
    type = models.CharField(
        _("Film Type"),
        choices=enums.FilmCategoryType.choices(),
        max_length=100,
        blank=False,
        null=False,
        help_text=_("The type of film e.g Series, Standalone")
    )
    duration = models.DurationField(_("Film duration(Runtime)"), null=True, blank=True)
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
        choices=enums.FilmSaleType.choices(), 
        default=enums.FilmSaleType.ONE_TIME_SALE.value,
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
    transaction = models.ForeignKey(
        to=Transaction,
        on_delete=models.PROTECT,
        null=True,
        blank=False,
        related_name="purchases",
        help_text=_("The transaction associated with this purchase")
    )
    payment_status = models.CharField(
        choices=enums.PurchasePaymentStatus.choices(),
        default=enums.PurchasePaymentStatus.PENDING.value,
        verbose_name=_("Purchase Payment Status")
    )
    status = models.CharField(
        choices=enums.PurchaseStatusType.choices(), 
        default=enums.PurchaseStatusType.REVOKED.value, 
        verbose_name=_("Purchase Status")
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


class Short(BaseModelMixin):
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="film_shorts",
        verbose_name=_("Owned By"),
    )
    film = models.ForeignKey(
        to="feed.Feed",
        on_delete=models.SET_NULL,
        null=True,
        blank=False,
        related_name="shorts",
        verbose_name=_("Film"),
        help_text=_("Film this short is related to"),
    )
    file = models.OneToOneField(
        to=FileModel,
        on_delete=models.CASCADE,
        related_name="short",
        null=False,
        blank=False,
        verbose_name=_("Short Media File"),
    )
    slug = models.SlugField(
        _("Slug"),
        max_length=255,
        blank=True,
        help_text=_("Auto-generated slug"),
    )
    type = models.CharField(
        _("Short Type"),
        max_length=50,
        choices=enums.ShortType.choices(),
        null=False,
        blank=False,
    )
    caption = models.TextField(
        _("Caption"),
        blank=True,
        help_text=_("A short caption for the short"),
    )
    duration = models.DurationField(_("Short Duration (Runtime)"), null=True, blank=True)
    language = models.CharField(
        _("Language"),
        max_length=2,
        default="en",
        help_text=_("Language code, e.g., 'en' for English"),
    )
    tags = ArrayField(
        base_field=models.CharField(max_length=50),
        default=list,
        blank=True,
        help_text=_("Optional list of tags for discovery"),
    )
    release_date = models.DateField(
        _("Release Date"),
        null=True,
        blank=True,
        help_text=_("The date this short was/will be released"),
    )
    is_released = models.BooleanField(
        _("Has the short been released?"),
        default=False,
        null=True,
        blank=True,
    )
    saved = models.ManyToManyField(
        to=User,
        verbose_name=_("Users Who Have Bookmarked this short"),
        related_name="bookmarked_shorts",
        blank=True,
    )
    views_count = models.BigIntegerField(default=0)
    likes_count = models.BigIntegerField(default=0)
    comments_count = models.BigIntegerField(default=0)

    class Meta:
        verbose_name = _("Short")
        verbose_name_plural = _("Shorts")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        base = self.slug or self.title
        return f"{base} (short)"
