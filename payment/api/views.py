from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, parser_classes, renderer_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer
from rest_framework.views import APIView
from rest_framework.generics import UpdateAPIView, ListAPIView
from rest_framework.exceptions import PermissionDenied, NotFound

from payment.api.serializers import TransactionSerializer
from payment.models import Transaction
from users.models import Wallet
from paylink.custom_permissions import WalletHasPin, WalletBalanceNotZero, TransactionDetailPerm

import requests
import random
import string


@api_view(['POST', ])
@permission_classes([IsAuthenticated, WalletHasPin, WalletBalanceNotZero])
@parser_classes([JSONParser, MultiPartParser])
def send_money(request):
    if request.method == "POST":
        wallet_number = request.query_params.get('wallet_number')
        try:
            wallet = Wallet.objects.get(wallet_number=wallet_number)
            if wallet.user == request.user:
                raise PermissionDenied
            else:
                serializer = TransactionSerializer(data=request.data)
                if serializer.is_valid(raise_exception=True):

                    # create transaction id
                    transaction_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(15))

                    transaction = serializer.save(sender=request.user, 
                                                recipient=wallet,
                                                transaction_id=transaction_id)
                    
                    # deduct transaction amount from sender's balance
                    request.user.wallet.balance -= transaction.amount
                    request.user.save()

                    data = {
                        'status': transaction.status,
                        'recipient': serializer.data.get('recipient'),
                        'amount': transaction.amount,
                        'transaction id': transaction.transaction_id,
                    }

                    return Response(data=data, status=status.HTTP_201_CREATED)
        except Wallet.DoesNotExist:
            raise NotFound(detail='wallet not found, please check the wallet number again')
    return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', ])
@permission_classes([IsAuthenticated, WalletHasPin])
@renderer_classes([JSONRenderer, BrowsableAPIRenderer])
def transaction_detail(request, transaction_id):
    try:
        transaction = Transaction.objects.get(transaction_id=transaction_id)
        if not TransactionDetailPerm().has_object_permission(request, None, transaction):
            raise PermissionDenied(detail='you cannot view this transaction')
        else:
            serializer = TransactionSerializer(transaction)
            data = serializer.data
            if request.user == transaction.sender:
                data.pop('sender')
            elif request.user == transaction.recipient.user:
                data.pop('recipient')

            return Response(data=data, status=status.HTTP_200_OK)
    except Transaction.DoesNotExist:
        raise NotFound(detail='this transaction does not exist, ensure you have added the right transaction id')