# from rest_framework import serializers
# from core.payment.models import Transaction
# from core.users.models import Wallet


# class ValidateBankSerializer(serializers.Serializer):
#     account_number = serializers.CharField(required=True)
#     account_bank = serializers.CharField(required=False)


# class TransactionSerializer(serializers.ModelSerializer):
#     sender = serializers.SerializerMethodField('get_sender_name')
#     sender_pin = serializers.IntegerField(required=True, write_only=True)

#     class Meta:
#         model = Transaction
#         fields = [
#                   'sender', 'recipient_name', 
#                   'recipient_account_number', 'recipient_bank', 
#                   'amount', 'transaction_id', 'status', 'narration',
#                   'sender_pin', 'transaction_type', 'sent_at'
#                 ]
#         extra_kwargs = {
#             'transaction_id': {'read_only': True},
#             'transaction_type': {'read_only': True},
#             'status': {'read_only': True},
#             'sent_at': {'read_only': True}
#         }


#     def get_sender_name(self, transaction):
#         name = transaction.sender.name
#         sender_wallet_number = transaction.sender.wallet.wallet_number
#         return name, sender_wallet_number
    

#     def validate_amount(self, value):
#         if value < 50:
#             raise serializers.ValidationError({'error':"you can't send an amount lesser than 50 naira"})
        
#         return value
    

#     def validate_sender_pin(self, value):
#         sender = self.context.get('request')
#         if len(str(value)) > 4:
#             raise serializers.ValidationError({'error': 'invalid pin length, pin should be 4 digits'})
#         elif value != sender.user.wallet.wallet_pin:
#             raise serializers.ValidationError({'error': 'incorrect pin'})
        
#         return value

#     def create(self, validated_data):
#         sender_pin = validated_data.pop('sender_pin', None)
#         transaction = Transaction.objects.create(**validated_data)
#         transaction.save()
#         return transaction