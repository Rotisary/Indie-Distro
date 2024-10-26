from django.contrib import admin
from payment.models import Transaction


class TransactionAdmin(admin.ModelAdmin):
    list_display = ['get_sender', 'get_recipient', 'amount', 'transaction_id', 'status']
    search_fields = [
        'sender__username', 
        'sender__name', 
        'recipient__user__name', 
        'recipient__user__username',
        'recipient__wallet_id',
        'transaction_id'
    ]
    list_select_related = ['sender', 'recipient']

    @admin.display(description='sender')
    def get_sender(self, obj):
        return obj.sender.name
    

    @admin.display(description='recipient')
    def get_recipient(self, obj):
        return obj.recipient.wallet_number


admin.site.register(Transaction, TransactionAdmin)
