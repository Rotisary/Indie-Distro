from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, authentication_classes, permission_classes, parser_classes, renderer_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer
from rest_framework.views import APIView
from rest_framework.generics import UpdateAPIView, ListAPIView
from rest_framework.exceptions  import PermissionDenied, NotFound

from payment.api.serializers import TransactionSerializer, ValidateBankSerializer
from payment.models import Transaction
from users.models import Wallet, Bank
from paylink.custom_permissions import WalletHasPin, WalletBalanceNotZero, TransactionDetailPerm
from .external_requests import validate_recipient_account, transfer_funds

from django.views.decorators.csrf import csrf_exempt
import logging
import json
import requests
import random
import string


@api_view(['POST', ])
@permission_classes([IsAuthenticated, WalletHasPin])
@parser_classes([JSONParser, MultiPartParser])
def validate_account(request):
        if request.method == "POST":
            serializer = ValidateBankSerializer(data=request.data)
            type = request.query_params.get('type') # get url query parameter if the account is internal or external
            if serializer.is_valid(raise_exception=True):
                user_account_number = serializer.validated_data['account_number']              
                if type == 'internal':  # check for type of account
                    try:
                        wallet = Wallet.objects.prefetch_related('sub_account').get(wallet_number=user_account_number)
                        account_number = wallet.sub_account.barter_id # get the barter_id of the associated flutterwave sub account

                        # call validate recipient account function
                        check = validate_recipient_account(
                            account_number = account_number,
                            account_bank = 'flutterwave'
                        )

                        if check['status'] == 'error':
                            return Response(data={'error': check['message']}, status=status.HTTP_400_BAD_REQUEST)
                        else:
                            response_data = {'account_name': wallet.user.name} # add the name of the wallet owner to the response
                            response_data.update(serializer.data)  
                            data = {
                                'details': response_data,
                                'complete_transaction_url': reverse('send-money', request=request) # reverse users to the send money endpoint
                            }
                            return Response(data=data, status=status.HTTP_200_OK)
                    except Wallet.DoesNotExist:
                        raise NotFound(detail='this account does not exist')
                elif type == 'external':
                    user_account_bank = serializer.validated_data['account_bank']
                    bank = Bank.objects.get(name=user_account_bank) # query the database for the bank with the inputed name 
                    check = validate_recipient_account(
                        account_number = user_account_number,
                        account_bank = bank.code # set the account bank parameter to the bank code
                    )
                    if check['status'] == 'error':
                        return Response(data={'error': check['message']}, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        response_data = {'account_name': check['data']['account_name']} # add the name of the account owner to the response
                        response_data.update(serializer.data) 
                        data = {
                            'details': response_data,
                            'complete_transaction_url': reverse('send-money', request=request)
                        }
                        return Response(data=data, status=status.HTTP_200_OK)
                else:
                    return Response(data={'error': 'bad request'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST', ])
@permission_classes([IsAuthenticated, WalletHasPin, WalletBalanceNotZero])
@parser_classes([JSONParser, MultiPartParser])
def send_money(request):
    if request.method == "POST":
        serializer = TransactionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid(raise_exception=True):
            wallet_number = serializer.validated_data['recipient_account_number']
            amount = serializer.validated_data['amount']
            type = request.query_params.get('type')
            transfer_funds_response = ''
            if type == 'internal':
                try:
                    wallet = Wallet.objects.get(wallet_number=wallet_number)
             
                    if wallet.user == request.user: # check if user is trying to send money to their own wallet
                        raise PermissionDenied
                    else:
                        # create transaction id
                        transaction_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(15))

                        if request.user.wallet.balance > amount: # check if sender has sufficient funds
                            transaction = serializer.save(sender=request.user, 
                                                        transaction_id=transaction_id,
                                                        transaction_type=type)
                            
                            wallet_sub_account = wallet.sub_account
                            bank = Bank.objects.get(name=wallet_sub_account.virtual_bank_name)

                            # call the transfer_funds function 
                            transfer_funds_response = transfer_funds(
                                bank = bank.code, # set the function's bank code and bank account number to the virtual bank and virtual bank account number of the wallet sub_account
                                account_number = wallet_sub_account.virtual_account_number,
                                amount = transaction.amount,
                                narration = transaction.narration,
                                reference = transaction.transaction_id,
                                recipient_name = f"Flutterwave/PAYOUTSUB {transaction.recipient_name}",
                                debit_account = wallet_sub_account.account_reference
                            )                       
                        else:
                            raise PermissionDenied(detail='insufficient funds, fund your account')
                except Wallet.DoesNotExist:
                    raise NotFound(detail="the recipient's wallet number is invalid")
            elif type == 'external': # create transaction without checking if recipient's wallet is user's wallet
                try:
                    wallet = Wallet.objects.get(wallet_number=wallet_number)
                    raise PermissionDenied(detail="this is an external transfer, you can't send money to an internal bank")
                except Wallet.DoesNotExist:
                    transaction_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(15))

                    if request.user.wallet.balance > amount: # check if sender has sufficient funds
                        transaction = serializer.save(sender=request.user, 
                                                    transaction_id=transaction_id,
                                                    transaction_type=type)
                        
                        # call the transfer funds function
                        transfer_funds_response, full_json_response = transfer_funds(
                            bank = transaction.recipient_bank,
                            account_number = transaction.recipient_account_number,
                            amount = transaction.amount,
                            narration = transaction.narration,
                            reference = transaction.transaction_id,
                            recipient_name = transaction.recipient_name,
                            debit_account = transaction.sender.wallet.sub_account.account_reference
                        )
                    else:
                        raise PermissionDenied(detail='insufficient funds, fund your account')
            else:
                return Response(data={'error': 'bad request'}, status=status.HTTP_400_BAD_REQUEST)

            response_data = serializer.data
            response_data.pop('sender')
            if transfer_funds_response == 'NEW':
                return Response(data=response_data, status=status.HTTP_201_CREATED)
            elif transfer_funds_response == 'FAILED':
                return Response(data=full_json_response['data']['complete_message'], status=status.HTTP_400_BAD_REQUEST)
            else: 
                return Response(data=transfer_funds_response, status=status.HTTP_400_BAD_REQUEST)    

    return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def retry_transaction(request, transaction_id):
    pass


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
            if transaction.transaction_type == 'internal':
                try:
                    wallet = Wallet.objects.get(wallet_number=transaction.recipient_account_number)
                    if request.user == transaction.sender:
                        data.pop('sender')
                    elif request.user.wallet == wallet:
                        data.pop('recipient_account_number')
                        data.pop('recipient_name')
                        data.pop('recipient_bank')
                except Wallet.DoesNotExist:
                    raise NotFound(detail="the recipient's wallet number is invalid")
            else:
                if request.user == transaction.sender:
                    data.pop('sender')   

            return Response(data=data, status=status.HTTP_200_OK)
    except Transaction.DoesNotExist:
        raise NotFound(detail='this transaction does not exist, ensure you have added the right transaction id')
    

logger = logging.getLogger(__name__)
@csrf_exempt
@api_view(['POST', ])
@authentication_classes([])
@parser_classes([JSONParser, MultiPartParser])
def event_webhooks(request):
    if request.method == "POST":
        secret_hash = '234AASD'
        flw_secret_hash = request.headers.get('verif-hash')
        if secret_hash == flw_secret_hash:
            try:
                payload = request.data
                logger.info("webhook data received: ", payload)
                transaction = Transaction.objects.get(transaction_id=payload['data']['reference'])
                if payload['data']['status'] == 'SUCCESSFUL':
                    sender = transaction.sender
                    if transaction.type == 'internal':       
                        recipient_wallet_number = transaction.recipient_account_number 
                        wallet = Wallet.objects.get(wallet_number=recipient_wallet_number)

                        # add transaction amount to recipient's wallet for internal transfers
                        wallet.balance += transaction.amount
                        wallet.save()

                        # deduct transaction amount from sender's balance
                        sender.wallet.balance -= transaction.amount
                        sender.save()
                    else:
                        # deduct transaction amount from sender's balance only for external transfers
                        sender.wallet.balance -= transaction.amount
                        sender.save()

                    transaction.status = 'successful'
                    transaction.save()
                elif payload['data']['status'] == 'FAILED':
                    transaction.status = 'failed'
                    transaction.save()
            except json.JSONDecodeError:
                logger.error("Failed to decode JSON data")
                return Response({"status": "error", "message": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)
            
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)