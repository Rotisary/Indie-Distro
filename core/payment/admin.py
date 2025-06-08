from django.contrib import admin
from core.payment.models import Transaction


class TransactionAdmin(admin.ModelAdmin):
    list_display = ['get_sender', 'recipient_name', 'amount', 'transaction_id', 'status', 'transaction_type']
    search_fields = [
        'sender__username', 
        'sender__name', 
        'recipient_name', 
        'recipient_bank',
        'recipient_account_number',
        'transaction_id'
    ]
    list_select_related = ['sender']

    @admin.display(description='sender')
    def get_sender(self, obj):
        return obj.sender.name


admin.site.register(Transaction, TransactionAdmin)
