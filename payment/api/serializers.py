from rest_framework import serializers
from payment.models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    sender = serializers.SerializerMethodField('get_sender_name')
    recipient = serializers.SerializerMethodField('get_recipient_name')

    class Meta:
        model = Transaction
        fields = ['sender', 'recipient', 'amount', 'transaction_id', 'status', 'narration', 'sent_at']
        extra_kwargs = {
            'transaction_id': {'read_only': True},
            'status': {'read_only': True},
            'sent_at': {'read_only': True}
        }


    def get_sender_name(self, transaction):
        name = transaction.sender.name
        sender_wallet_number = transaction.sender.wallet.wallet_number
        return name, sender_wallet_number
    

    def get_recipient_name(self, transaction):
        name = transaction.recipient.user.name
        recipient_wallet_number = transaction.recipient.wallet_number
        return name, recipient_wallet_number
    

    def validate_amount(self, value):
        if value < 50:
            raise serializers.ValidationError({'error':"you can't send an amount lesser than 50 naira"})
        
        return value

    def create(self, validated_data):
        transaction = Transaction.objects.create(**validated_data)
        transaction.save()
        return transaction