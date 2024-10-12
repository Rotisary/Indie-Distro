from django.contrib import admin
from payment.models import Transaction


class TransactionAdmin(admin.ModelAdmin):
    list_display = ['sender__username', 'recipient__wallet_id', 'amount', 'transaction_id']
    search_fields = [
        'sender__username', 
        'sender__name', 
        'recipient__user__name', 
        'recipient__user__username',
        'recipient__wallet_id',
        'transaction_id'
    ]


admin.site.register(Transaction, TransactionAdmin)
