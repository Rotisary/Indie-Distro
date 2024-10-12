from django.db import models
from django.conf import settings
from users.models import Wallet


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
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, 
                               related_name='transactions',
                               null=False,
                               blank=False,
                               on_delete=models.DO_NOTHING)
    recipient = models.ForeignKey(Wallet,
                                  related_name='money_received',
                                  null=False,
                                  blank=False,
                                  on_delete=models.DO_NOTHING)
    transaction_id = models.CharField(max_length=15,
                                      null=False,
                                      blank=False,
                                      unique=True)
    amount = models.IntegerField(default=50,
                                 null=False,
                                 blank=False)
    status = models.CharField(choices=STATUS_CHOICES, default=PENDING)
    narration = models.TextField(max_length=50,
                                 null=True,
                                 blank=True)
    sent_at = models.DateTimeField(auto_now_add=True,
                                   null=False,
                                   blank=False)

    objects = models.Manager()


    def __str__(self):
        return f"{self.id}"
    

    def save(self, *args, **kwargs):
        if not self.id:
            self.recipient.balance += self.amount
            self.recipient.save()
        return super(Transaction, self).save(*args, **kwargs)



# total = 5
# for i in range(4):
#     total /= 2
#     print(total)