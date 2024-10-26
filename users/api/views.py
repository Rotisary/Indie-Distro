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

from django.contrib.auth import authenticate



from users.models import User, Wallet, Bank
from users.api.serializers import (
    UserSerializer, 
    UserUpdateSerializer, 
    PasswordChangeSerializer, 
    WalletSerializer
)
from paylink.custom_permissions import WalletHasPin

import requests

@api_view(['POST', ])
def register(request):
    if request.method == 'POST':
        serializer = UserSerializer(data=request.data)
        data = {}
        if serializer.is_valid(raise_exception=True):
            user = serializer.save()
            token = Token.objects.get(user=user)
            data['message'] = 'user registered succesfully'
            data['details'] = serializer.data
            data['token'] = token.key
            return Response(data=data, status=status.HTTP_201_CREATED)
        else:
            return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ObtainAuthTokenView(APIView):
    authentication_classes = []
    permission_classes = []
    parser_classes = [JSONParser, MultiPartParser]
    

    def post(self, request):
        data = {}

        email = request.data.get('email')
        password = request.data.get('password')

        account = authenticate(email=email, password=password)

        if account is not None:
            try:
                token = Token.objects.get(user=account).key
            except Token.DoesNotExist:
                create_token = Token.objects.create(user=account)
                token = create_token.key

            data['response'] = 'Successfully Authenticated'
            data['pk'] = account.pk
            data['email'] = account.email
            data['token'] = token
            status_code = status.HTTP_200_OK
        else:
            data['response'] = 'error'
            data['error_message'] = 'Invalid credentials'
            status_code = status.HTTP_400_BAD_REQUEST  
        return Response(data=data, status=status_code)


@api_view(['GET', ])
@permission_classes([IsAuthenticated, ])
@renderer_classes([JSONRenderer, BrowsableAPIRenderer])
def user_detail_view(request, username):
    try:
        user = User.objects.get(username=username)

        if request.user != user:
            raise PermissionDenied
        else:
            if request.method == 'GET':
                serializer = UserSerializer(user)
                data = serializer.data
                return Response(data=data)
    except User.DoesNotExist:
        raise NotFound(detail='this user does not exist')



@api_view(['PUT', ])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, MultiPartParser])
def update_user_detail_view(request, username):
    try:
        user = User.objects.get(username=username)
    
        if request.user != user:
             raise PermissionDenied
        else:
            if request.method == 'PUT':
                serializer = UserUpdateSerializer(user, data=request.data, partial=True)
                data = {}
                if serializer.is_valid(raise_exception=True):
                    serializer.save()
                    data['success'] = 'update successful'
                    return Response(data=data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except User.DoesNotExist:
        raise NotFound(detail='this user does not exist')
    

@api_view(['DELETE', ])
@permission_classes([IsAuthenticated])
def delete_user_view(request, username):
    try:
        user = User.objects.get(username=username)
   
        if request.user != user:
            raise PermissionDenied
        else:
            data = {}
            if request.method == 'DELETE':
                operation = user.delete()
                if operation:
                    data['success'] = 'delete successful'
                    status_code = status.HTTP_200_OK
                else:
                    data['error'] = 'failed to delete user'
                    status_code = status.HTTP_400_BAD_REQUEST
                
                return Response(data=data, status=status_code)
    except User.DoesNotExist:
        raise NotFound(detail='this user has already been deleted')
    

class PasswordChangeView(UpdateAPIView):
    authentication_classes = ([TokenAuthentication, ])
    permission_classes = ([IsAuthenticated, ])
    parser_classes = [JSONParser, MultiPartParser]
    serializer_class = PasswordChangeSerializer
    model = User


    def get_object(self, queryset=None):
        obj = self.request.user
        return obj 
 
    
    def update(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(data=request.data)


        if serializer.is_valid(raise_exception=True):
            new_password = serializer.validated_data['new_password']
            confirm_password = serializer.validated_data['confirm_password']
            if not self.object.check_password(serializer.validated_data['old_password']):
                return Response({
                    'old_password': 'wrong password! please enter correct password'}, 
                    status=status.HTTP_400_BAD_REQUEST
                    )

            if confirm_password != new_password:
                return Response({
                    'confirm password': 'the passwords must match!'}, 
                    status=status.HTTP_400_BAD_REQUEST
                    )
            
            self.object.set_password(new_password)
            self.object.save()
            return Response({
                'password': 'password changed successfully!'}, 
                status=status.HTTP_200_OK
                )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', ])
@permission_classes([IsAuthenticated, ])
@parser_classes([JSONParser, MultiPartParser])
def update_wallet_view(request, id):
    try:
        wallet = Wallet.objects.get(wallet_id=id)

        if request.user != wallet.user:
            raise PermissionDenied
        else:
            if request.method == "PUT":
                data = {}
                serializer = WalletSerializer(wallet, 
                                            data=request.data, 
                                            partial=True, 
                                            context={'request': request})
                if serializer.is_valid(raise_exception=True):
                    serializer.save()
                    data['success'] = 'your wallet is ready' 
                    return Response(data=data, status=status.HTTP_200_OK)
            return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Wallet.DoesNotExist:
        raise NotFound(detail='wallet does not exist')
    

@api_view(['GET', ])
@permission_classes([IsAuthenticated, WalletHasPin])
@parser_classes([JSONRenderer, BrowsableAPIRenderer])
def wallet_view(request, wallet_id):
    try:
        wallet = Wallet.objects.get(user=request.user)

        if request.method == "GET":
            serializer = WalletSerializer(wallet, context={'request': request})
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Wallet.DoesNotExist:
        raise NotFound(detail='wallet does not exist')