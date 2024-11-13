from django.db import models
from django.conf import settings
from users.models import Wallet
from payment.api import external_requests

# class TransactionManager(models.Manager):
#     def get_queryset(self):
#         return super().get_queryset().filter(is_listed=True)
    

class Transaction(models.Model):
    PENDING = 'pending'
    SUCCESSFUL = 'successful'
    FAILED = 'failed'
    STATUS_CHOICES = [
        (PENDING, 'pending'),
        (SUCCESSFUL, 'successful'),
        (FAILED, 'failed')
    ]
    INTERNAL = 'internal'
    EXTERNAL = 'external'
    TRANSACTION_TYPE_CHOICES = [
        (INTERNAL, 'internal'),
        (EXTERNAL, 'external')
    ]
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, 
                               related_name='transactions',
                               null=False,
                               blank=False,
                               on_delete=models.DO_NOTHING)
    recipient_bank = models.CharField(max_length=225,
                                      blank=True,
                                      null=True)
    recipient_account_number = models.CharField(max_length=10,
                                                null=False,
                                                blank=False)
    recipient_name = models.CharField(max_length=225,
                                      null=False,
                                      blank=False)
    transaction_id = models.CharField(max_length=15,
                                      null=False,
                                      blank=False,
                                      unique=True)
    flw_transfer_id = models.IntegerField(null=True, blank=True)
    amount = models.FloatField(default=50,
                                 null=False,
                                 blank=False)
    status = models.CharField(choices=STATUS_CHOICES, default=PENDING)
    narration = models.TextField(max_length=50,
                                 null=True,
                                 blank=True)
    transaction_type = models.CharField(choices=TRANSACTION_TYPE_CHOICES,
                                        max_length=50,
                                        blank=True,
                                        null=True)
    sent_at = models.DateTimeField(auto_now_add=True,
                                   null=False,
                                   blank=False)

    objects = models.Manager()


    def __str__(self):
        return f"{self.id}" 