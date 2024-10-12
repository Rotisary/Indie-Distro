from rest_framework import serializers
from users.models import User, Wallet
from itertools import chain 
import string

class UserSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(style={'input_type': 'password'}, write_only=True)

    class Meta:
        model = User 
        fields = ['id', 'email', 'username', 'name', 'phone_number', 'age', 'password', 'confirm_password', 'ip_address']
        extra_kwargs = {
            'password': {'write_only': True},
            'id': {'read_only': True},
            'ip_address': {'read_only': True}
        }


    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({'error': 'confirm password does not match password'})
        
        return data
    

    def validate_phone_number(self, value):
        if len(value) == 11:
            letters = chain(range(ord('A'), ord('z') + 1), range(ord('a'), ord('z') + 1))
            for char in letters:
                if chr(char) in value:
                    raise serializers.ValidationError({'error': 'phone number is in invalid format, please use digits only!'})
        else:
            raise serializers.ValidationError({'error': 'your phone number can not be longer or shorter than eleven digits!'})
        
        return value
    

    
    def create(self, validated_data):
        password_two = validated_data.pop('confirm_password', None)
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user
    

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'username', 'name', 'phone_number'] 

    
    def validate_phone_number(self, value):
        if len(value) == 11:
            letters = chain(range(ord('A'), ord('z') + 1), range(ord('a'), ord('z') + 1))
            for char in letters:
                if chr(char) in value:
                    raise serializers.ValidationError({'error': 'phone number is in invalid format, please use digits only!'})
        else:
            raise serializers.ValidationError({'error': 'your phone number can not be longer or shorter than eleven digits!'})
        
        return value


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True) 
    confirm_password = serializers.CharField(write_only=True, required=True) 


class WalletSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Wallet
        fields = ['wallet_id', 'user', 'wallet_number', 'balance', 'wallet_pin']
        extra_kwargs ={
            'wallet_id': {'read_only': True},
            'user': {
                'view_name': 'user-detail',
                'read_only': True,
                'lookup_field': 'username'
            },
            'wallet_number': {'read_only': True},
            'wallet_pin': {'write_only': True}
        }


    def validate_wallet_pin(self, value):
        if len(str(value)) != 4:
            raise serializers.ValidationError({'error': 'pin should be 4 digits'})
        
        return value
        