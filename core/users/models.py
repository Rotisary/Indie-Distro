from django.db import models
from django.contrib.auth.models import  AbstractBaseUser, BaseUserManager

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from rest_framework.authtoken.models import Token
from users.api.external_requests import create_flw_subaccount


import random
import string

class UserManager(BaseUserManager):
    def create_user(self, email, username, name, phone_number, age, password=None):
        if not email:
            raise ValueError('users must have an email')
        if not username:
            raise ValueError('users must have an username')
        if not name:
            raise ValueError('users must have a name')
        if not phone_number:
            raise ValueError('users must enter their phone number')
        if not age:
            raise ValueError('users must enter their age')
        

        user = self.model(
            email = self.normalize_email(email),
            username = username,
            name = name,
            phone_number = phone_number,
            age = age
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, name, phone_number, age, password):
        user = self.create_user(
            email = self.normalize_email(email),
            username = username,
            name = name,
            phone_number = phone_number,
            age = age,
            password = password
        )
        
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user
    

class User(AbstractBaseUser):
    email = models.EmailField(verbose_name='email', 
                              unique=True, 
                              null=False, 
                              blank=False)
    username = models.CharField(max_length=30, 
                                unique=True, 
                                null=False, 
                                blank=False)
    name = models.CharField(max_length=200, null=False, blank=False)
    phone_number = models.CharField(max_length=20, null=False, blank=False, unique=True)
    age = models.IntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True, null=False)
    last_login = models.DateTimeField(auto_now=True, null=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'name', 'phone_number', 'age']

    objects = UserManager()


    def __str__(self):
        return f"{self.username}"
    

    def has_perm(self, perm, obj=None):
        return self.is_admin
    

    def has_module_perms(self, app_label):
        return True


class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                blank=False,
                                null=False,
                                related_name='wallet', 
                                on_delete=models.CASCADE)
    wallet_id = models.CharField(max_length=8, 
                                 blank=False,
                                 null=False,
                                 unique=True)
    wallet_number = models.CharField(max_length=10,
                                      null=False, 
                                      blank=False,
                                      unique=True)                                          
    balance = models.FloatField(default=0)
    wallet_pin = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
                                     
    

    def __str__(self):
        return f"{self.wallet_id}"


    def save(self, *args, **kwargs):
        if not self.id:
            self.wallet_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(8))
            self.wallet_number = ''.join(random.choice(string.digits) for x in range(10))
        return super(Wallet, self).save(*args, **kwargs)
    


class SubAccount(models.Model):
    wallet = models.OneToOneField(Wallet, 
                                  related_name='sub_account', 
                                  null=True,
                                  blank=True,
                                  on_delete=models.CASCADE)
    account_reference = models.CharField(max_length=20,
                                         null=False, 
                                         blank=False)
    barter_id = models.CharField(max_length=15,
                                 null=False,
                                 blank=False)
    virtual_account_number = models.CharField(max_length=10,
                                              blank=False,
                                              null=False)
    virtual_bank_name = models.CharField(max_length=100,
                                         blank=False,
                                         null=False)
    created_at = models.DateTimeField(null=True, blank=True)
    

    def __str__(self):
        return f"{self.wallet.wallet_number}'s subaccount"
    

class Bank(models.Model):
    code = models.CharField(max_length=10, blank=False, null=False)
    name = models.CharField(max_length=225, blank=False, null=False)

    def __str__(self):
        return f"{self.name}"
    
    
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_token(sender, instance, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_wallet(sender, instance, created=False, **kwargs):
    if created:
        Wallet.objects.create(user=instance)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_wallet(sender, instance, **kwargs):
    instance.wallet.save()


@receiver(post_save, sender=Wallet)
def create_subaccount(sender, instance, created=False, **kwargs):
    if created:
        create_flw_subaccount(
            sub_account = SubAccount, 
            wallet_instance = instance,
            name = instance.user.name, 
            email = instance.user.email,
            phone_number = instance.user.phone_number
        )

    
@receiver(post_save, sender=Wallet)
def save_subaccount(sender, instance, **kwargs):
    instance.sub_account.save()
