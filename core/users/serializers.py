from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.hashers import make_password
from core.users.models import User
from phonenumbers import parse, is_valid_number
from phonenumbers.phonenumberutil import  NumberParseException


class BaseUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "is_creator",
            "phone_number",
            "date_added",
        ]


class UserSerializer:
    class Retrieve(serializers.ModelSerializer):
        class Meta:
            model = User
            exclude = [
                "password",
                "is_active",
                "ban_duration_in_minutes",
                "ban_expiry_date",
                "date_added",
                "date_last_modified",
                "groups",
                "user_permissions",
                "last_login",
            ]
    
    class Create(serializers.ModelSerializer):
        password2 = serializers.CharField(
            write_only=True,
            required=True,
            style={"input_type": "password"},
            help_text=_("Confirm Password"),
        )

        class Meta:
            model = User
            fields = [
                "email",
                "first_name",
                "last_name",
                "username",
                "phone_number",
                "is_phone_number_verified",
                "is_email_verified",
                "bio",
                "gender",
                "dob",
                "is_banned",
                "account_type",
                "location",
                "password",
                "password2",
            ]

        def validate(self, attrs):
            password = attrs.get("password")
            password2 = attrs.pop("password2", None)

            if password and password2 and password != password2:
                raise serializers.ValidationError(
                    {"password": _("Passwords do not match.")}
                )

            return attrs
        
        def validate_phone_number(self, value):
            value = ("+" + value) if not value.startswith("+") else value
            try:
                phone_number_instance = parse(value)
                if not is_valid_number(phone_number_instance):
                    message = (
                        f"Kindly provide a valid phone number, Note: Phone number must be provided in "
                        f"international format and must start with '+'"
                    )
                    raise serializers.ValidationError(message, "invalid phone number")
            except NumberParseException as err:
                message = err._msg
                raise serializers.ValidationError(message, "invalid phone number")
            return value
        
        def create(self, validated_data):
            validated_data["password"] = make_password(validated_data["password"])
            return super().create(validated_data)
        
        
    class Update(serializers.ModelSerializer):

        class Meta:
            model = User
            fields = [
                "first_name",
                "last_name",
                "username",
                "phone_number",
                "is_phone_number_verified",
                "is_email_verified",
                "bio",
                "gender",
                "is_banned",
                "location",
            ]
        
        def validate_phone_number(self, value):
            value = ("+" + value) if not value.startswith("+") else value
            try:
                phone_number_instance = parse(value)
                if not is_valid_number(phone_number_instance):
                    message = (
                        f"Kindly provide a valid phone number, Note: Phone number must be provided in "
                        f"international format and must start with '+'"
                    )
                    raise serializers.ValidationError(message, "invalid phone number")
            except NumberParseException as err:
                message = err._msg
                raise serializers.ValidationError(message, "invalid phone number")
            return value
        

class AuthSerializer:
    class Login(serializers.Serializer):
        email = serializers.EmailField(required=True, help_text=_("Email"))
        password = serializers.CharField(
            write_only=True, required=True, style={"input_type": "password"}, help_text=_("Password")
        )

    class TokenRefresh(serializers.Serializer):
        refresh = serializers.CharField(
            required=True,
            help_text=_("This is the 'refresh' key in account AccessToken"),
        ) 


# class WalletSerializer(serializers.HyperlinkedModelSerializer):
#     class Meta:
#         model = Wallet
#         fields = ['wallet_id', 'user', 'wallet_number', 'balance', 'wallet_pin']
#         extra_kwargs ={
#             'wallet_id': {'read_only': True},
#             'user': {
#                 'view_name': 'user-detail',
#                 'read_only': True,
#                 'lookup_field': 'username'
#             },
#             'wallet_number': {'read_only': True},
#             'wallet_pin': {'write_only': True}
#         }


#     def validate_wallet_pin(self, value):
#         if len(str(value)) != 4:
#             raise serializers.ValidationError({'error': 'pin should be 4 digits'})
        
#         return value
        