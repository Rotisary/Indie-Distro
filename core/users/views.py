from loguru import logger
from django.conf import settings
from django.contrib.auth import authenticate

from rest_framework import status, response, views
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticated

from core.users.models import User, UserSession
from core.users.serializers import UserSerializer, AuthSerializer
from core.utils import exceptions
from utils.permissions import IsGuestUser



# from core.users.models import User, Wallet, Bank
# from core.users.api.serializers import (
#     UserSerializer, 
#     UserUpdateSerializer, 
#     PasswordChangeSerializer, 
#     WalletSerializer
# )
# # from paylink.custom_permissions import WalletHasPin

# import requests

class CreateUser(views.APIView):
    http_method_names = ['post']
    permission_classes = [IsGuestUser, ]
    parser_classes = [JSONParser, ]


    @extend_schema(
        auth=[],
        description="endpoint for user creation",
        request=UserSerializer.Create,
        responses={201: UserSerializer.Retrieve},
    )
    def post(self, request):
        serializer = UserSerializer.Create(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = serializer.save()
        logger.info(f"created user with email {account.email}")

        auth_token = account.retrieve_auth_token()
        logger.info(f"\n\nUser Auth\n{auth_token}")

        logger.info("CREATING SESSION FOR THE NEW USER")
        UserSession.objects.create(
            user=account,
            refresh=auth_token["refresh"],
            access=auth_token["access"],
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT"),
            is_active=True,
        )

        serializer = UserSerializer.Retrieve(instance=account)
        response_data = {"user": serializer.data, "token": auth_token}
        return response.Response(response_data, status=status.HTTP_201_CREATED)
    

class RetrieveUpdateUser(views.APIView):
    http_method_names = ["get", "patch"]
    permission_classes = [IsAuthenticated, ]
    renderer_classes = [JSONRenderer, ]


    @extend_schema(
        description="endpoint for retrieving details of the authenticated user",
        request=None,
        responses={200: UserSerializer.Retrieve},
    )
    def get(self, request):
        serializer = UserSerializer.Retrieve(request.user)
        return response.Response(serializer.data, status=status.HTTP_200_OK)
    
    @extend_schema(
        description="endpoint for updating details of the authenticated user",
        request=UserSerializer.Update, 
        responses={200: UserSerializer.Retrieve},
    )
    def patch(self, request):
        serializer = UserSerializer.Update(
            instance=request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        serializer = UserSerializer.Retrieve(instance=user)
        response_data = {"message": "details successfully updated", "data": serializer.data}
        return response.Response(data=response_data, status=status.HTTP_200_OK)
    

class Login(views.APIView):
    http_method_names = ['post']
    permission_classes = [IsGuestUser, ]
    parser_classes = [JSONParser, ]


    @extend_schema(
        auth=[],
        description="endpoint for user login",
        request=AuthSerializer.Login,
        responses={200: UserSerializer.Retrieve},
    )
    def post(self, request):
        serializer = AuthSerializer.Login(data=request.data)
        serializer.is_valid(raise_exception=True)
        email=serializer.validated_data["email"]
        password=serializer.validated_data["password"]
        account = authenticate(request, email=email, password=password)

        if not account:
            logger.error("Authentication failed")
            raise exceptions.CustomException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Invalid credentials"
            )

        auth_token = account.retrieve_auth_token()
        logger.info(f"\n\nUser Auth\n{auth_token}")
        session = UserSession.objects.filter(user=account).first()

        if session:
            logger.info("SESSION EXISTS")
            try:
                token = RefreshToken(session.refresh)
                token.blacklist()
            except Exception as e:
                raise exceptions.CustomException(message="unable to blacklist token")
            session.delete()
            logger.info("OLD SESSION DELETED")

        logger.info("CREATING NEW SESSION")
        UserSession.objects.create(
            user=account,
            refresh=auth_token["refresh"],
            access=auth_token["access"],
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT"),
            is_active=True,
        )
        logger.info(f"User {account.email} logged in successfully")

        response_data = {"user": UserSerializer.Retrieve(instance=account).data, "token": auth_token}
        return response.Response(response_data, status=status.HTTP_200_OK)
    

class Logout(views.APIView):
    http_method_names = ['post']
    permission_classes = [IsAuthenticated, ]


    @extend_schema(
        description="endpoint for user logout",
        request=None,
        responses={200: None},
    )
    def post(self, request):
        try:
            session = UserSession.objects.filter(user=request.user).first()
            if session:
                token = RefreshToken(session.refresh)
                token.blacklist()
                session.delete()
                logger.info(f"User {request.user.email} logged out successfully")
                return response.Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)
            raise exceptions.CustomException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="this user is not authenticated"
            )
        except TokenError as err:
            raise exceptions.CustomException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=str(err),
                errors=["refresh token error"],
            )
        

class TokenRefresh(views.APIView):
    http_method_names = ['post']
    permission_classes = []
    parser_classes = [JSONParser, ]


    @extend_schema(
        description="endpoint for refreshing user access token after it expires",
        request=AuthSerializer.TokenRefresh,
        responses={200: None}
    )
    def post(self, request):
        serializer = AuthSerializer.TokenRefresh(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh_token = serializer.validated_data["refresh"]
        try:
            session = UserSession.objects.get(refresh=refresh_token)
            RefreshToken(refresh_token).blacklist()

            token = session.user.retrieve_auth_token()
            session.access = token["access"]
            session.refresh = token["refresh"]
            session.save()
            return response.Response(status=status.HTTP_200_OK, data=token)

        except TokenError as err:
            raise exceptions.CustomException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=str(err),
                errors=["refresh token error"],
            )
        except UserSession.DoesNotExist:
            raise exceptions.CustomException(
                message="Session not found.",
            )


# @api_view(['PUT', ])
# @permission_classes([IsAuthenticated, ])
# @parser_classes([JSONParser, MultiPartParser])
# def update_wallet_view(request, id):
#     try:
#         wallet = Wallet.objects.get(wallet_id=id)

#         if request.user != wallet.user:
#             raise PermissionDenied
#         else:
#             if request.method == "PUT":
#                 data = {}
#                 serializer = WalletSerializer(wallet, 
#                                             data=request.data, 
#                                             partial=True, 
#                                             context={'request': request})
#                 if serializer.is_valid(raise_exception=True):
#                     serializer.save()
#                     data['success'] = 'your wallet is ready' 
#                     return Response(data=data, status=status.HTTP_200_OK)
#             return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#     except Wallet.DoesNotExist:
#         raise NotFound(detail='wallet does not exist')
    

# @api_view(['GET', ])
# @permission_classes([IsAuthenticated, WalletHasPin])
# @parser_classes([JSONRenderer, BrowsableAPIRenderer])
# def wallet_view(request, wallet_id):
#     try:
#         wallet = Wallet.objects.get(user=request.user)

#         if request.method == "GET":
#             serializer = WalletSerializer(wallet, context={'request': request})
#             return Response(data=serializer.data, status=status.HTTP_200_OK)
#         return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#     except Wallet.DoesNotExist:
#         raise NotFound(detail='wallet does not exist')
