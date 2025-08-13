from django.db import models
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import (
    BaseUserManager,
    AbstractBaseUser,
    PermissionsMixin,
)
from django.contrib.postgres.fields import ArrayField
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from rest_framework.authtoken.models import Token
# from users.api.external_requests import create_flw_subaccount

from rest_framework_simplejwt.tokens import RefreshToken

from core.utils import enums
from core.utils import mixins
# from core.utils.commons.utils.parsers import Parsers
# from core.utils.exceptions import WalletException


import random
import string

class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(
        self, email: str, first_name: str, last_name: str, username: str, password: str, **extra_fields
    ):
        if not email:
            raise ValueError("The email field is required")
        if not first_name:
            raise ValueError("The first name field is required")
        if not last_name:
            raise ValueError("The last name field is required")
        if not username:
            raise ValueError("The username field is required")
        
        email = self.normalize_email(email)
        user = self.model(
            email=email, 
            first_name=first_name, 
            last_name=last_name, 
            username=username,
            **extra_fields
        )
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(
            self, email: str, first_name: str, last_name: str, username: str, password: str = None, **extra_fields
        ):
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, first_name, last_name, username, password, **extra_fields)

    def create_superuser(
        self,
        email: str,
        first_name: str, 
        last_name: str, 
        username: str,
        password: str,
        account_type: str = enums.UserAccountType.SUPER_ADMINISTRATOR.value,
        **extra_fields,
    ):
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_staff", True)

        assert (
            account_type == enums.UserAccountType.SUPER_ADMINISTRATOR.value
            and account_type in enums.UserAccountType.values()
        )
        extra_fields.setdefault("account_type", account_type)
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, first_name, last_name, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, mixins.BaseModelMixin):
    first_name = models.CharField(
        _("First Name"), null=True, blank=True, max_length=255
    )
    last_name = models.CharField(_("Last Name"), null=True, blank=True, max_length=255)
    username = models.CharField(
        _("Username"), null=True, blank=True, max_length=50, unique=True
    )
    bio = models.CharField(_("About Me"), null=True, blank=True, max_length=120)
    email = models.EmailField(
        _("Email"), null=False, blank=False, max_length=225, unique=True
    )
    is_email_verified = models.BooleanField(
        _("Email Verified?"), default=False, blank=True, null=False
    )
    is_verified = models.BooleanField(_("Account Verified?"), default=False)

    account_type = models.CharField(
        _("Account Type"),
        choices=enums.UserAccountType.choices(),
        null=False,
        blank=True,
        default=enums.UserAccountType.USER.value,
        max_length=20,
    )

    dob = models.DateField(_("Date of Birth"), null=True, blank=True)
    gender = models.CharField(
        _("Gender"),
        choices=enums.UserGenderType.choices(),
        null=True,
        blank=True,
        max_length=50,
    )

    is_banned = models.BooleanField(
        _("User account has been banned"), null=False, blank=False, default=False
    )

    ban_expiry_date = models.DateTimeField(
        _("User account ban expiry date"), null=True, blank=True
    )

    ban_duration_in_minutes = models.PositiveIntegerField(
        _("Ban duration in minutes"), null=False, blank=False, default=0
    )

    phone_number = models.CharField(
        _("Phone Number"), max_length=50, null=True, blank=True, unique=True
    )
    is_phone_number_verified = models.BooleanField(
        _("Phone Number Verified?"), default=False, blank=True, null=False
    )
    location = models.CharField(
        _("Location (State, Country)"), null=True, blank=False, max_length=255
    )

    total_earned = models.DecimalField(
        _("Total Earned"),
        default=0,
        max_digits=15,
        decimal_places=2,
        null=False,
        blank=True,
    )
    has_pending_issues = models.BooleanField(
        _("Has Pending Issue?"), default=False, blank=True, null=False
    )
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = ["first_name", "last_name", "username"]

    objects = UserManager()


class UserSession(mixins.BaseModelMixin):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    refresh = models.CharField(max_length=255, unique=True, null=True, blank=True)
    access = models.CharField(max_length=255, unique=True, null=True, blank=True)
    ip_address = models.CharField(max_length=255, null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "User Session"
        verbose_name_plural = "User Sessions"

    def __str__(self):
        return f"{self.user.email} - {self.ip_address}"


# class Wallet(models.Model):
#     user = models.OneToOneField(settings.AUTH_USER_MODEL,
#                                 blank=False,
#                                 null=False,
#                                 related_name='wallet', 
#                                 on_delete=models.CASCADE)
#     wallet_id = models.CharField(max_length=8, 
#                                  blank=False,
#                                  null=False,
#                                  unique=True)
#     wallet_number = models.CharField(max_length=10,
#                                       null=False, 
#                                       blank=False,
#                                       unique=True)                                          
#     balance = models.FloatField(default=0)
#     wallet_pin = models.IntegerField(null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
                                     
    

#     def __str__(self):
#         return f"{self.wallet_id}"


#     def save(self, *args, **kwargs):
#         if not self.id:
#             self.wallet_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(8))
#             self.wallet_number = ''.join(random.choice(string.digits) for x in range(10))
#         return super(Wallet, self).save(*args, **kwargs)
 

# class SubAccount(models.Model):
#     wallet = models.OneToOneField(Wallet, 
#                                   related_name='sub_account', 
#                                   null=True,
#                                   blank=True,
#                                   on_delete=models.CASCADE)
#     account_reference = models.CharField(max_length=20,
#                                          null=False, 
#                                          blank=False)
#     barter_id = models.CharField(max_length=15,
#                                  null=False,
#                                  blank=False)
#     virtual_account_number = models.CharField(max_length=10,
#                                               blank=False,
#                                               null=False)
#     virtual_bank_name = models.CharField(max_length=100,
#                                          blank=False,
#                                          null=False)
#     created_at = models.DateTimeField(null=True, blank=True)
    

#     def __str__(self):
#         return f"{self.wallet.wallet_number}'s subaccount"
    

# class Bank(models.Model):
#     code = models.CharField(max_length=10, blank=False, null=False)
#     name = models.CharField(max_length=225, blank=False, null=False)

#     def __str__(self):
#         return f"{self.name}"
    
    
# @receiver(post_save, sender=settings.AUTH_USER_MODEL)
# def create_token(sender, instance, created=False, **kwargs):
#     if created:
#         Token.objects.create(user=instance)


# @receiver(post_save, sender=settings.AUTH_USER_MODEL)
# def create_wallet(sender, instance, created=False, **kwargs):
#     if created:
#         Wallet.objects.create(user=instance)


# @receiver(post_save, sender=settings.AUTH_USER_MODEL)
# def save_wallet(sender, instance, **kwargs):
#     instance.wallet.save()


# @receiver(post_save, sender=Wallet)
# def create_subaccount(sender, instance, created=False, **kwargs):
#     if created:
#         create_flw_subaccount(
#             sub_account = SubAccount, 
#             wallet_instance = instance,
#             name = instance.user.name, 
#             email = instance.user.email,
#             phone_number = instance.user.phone_number
#         )

    
# @receiver(post_save, sender=Wallet)
# def save_subaccount(sender, instance, **kwargs):
#     instance.sub_account.save()
