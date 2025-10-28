from django.db import models


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