import datetime

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from core.users.serializers import BaseUserSerializer
from .models import Feed, Short, Purchase
from core.file_storage.models import FileModel
from core.utils.exceptions import exceptions
from core.utils import enums


class BaseFilmSerializer(serializers.ModelSerializer):

    class Meta:
        model = Feed
        fields = [
            "id",
            "title",
            "plot",
            "release_date",
            "duration",
            "genre",
            "type"
        ]


class FeedSerializer:
    class FeedCreate(serializers.ModelSerializer):
        class Meta:
            model = Feed
            exclude = [
                "duration",
                "slug",
                "saved",
                "is_released",
                "date_added",
                "date_last_modified"
            ]
        

        def validate_cast(self, value):
            if len(value) > 5:
                raise serializers.ValidationError("Cannot have more than 5 major actors.")
            return value
        

        def validate_crew(self, value):
            if len(value) > 5:
                raise serializers.ValidationError("Cannot have more than 5 crew members.")
            return value
        
        def validate_release_date(self, value):
            if value and value <= datetime.date.today():
                raise serializers.ValidationError(
                    "Release date cannot be today. Please set a date later than today."
                )
            return value
        
    
    class FeedRetrieve(serializers.ModelSerializer):
        owner = BaseUserSerializer()

        class Meta:
            model = Feed
            exclude = ["saved", "date_last_modified"]

    
class ShortSerializer:
    class ShortCreate(serializers.ModelSerializer):
        film = serializers.PrimaryKeyRelatedField(
            queryset=Feed.objects.all(),
            required=True,
            allow_null=False,
            help_text=_("The film this short is associated with, if any.")
        )
        class Meta:
            model = Short
            exclude = [
                "duration",
                "slug",
                "saved",
                "views_count",
                "likes_count",
                "comments_count",
                "is_released",
                "date_added",
                "date_last_modified",
            ]

        def validate_release_date(self, value):
            if value and value <= datetime.date.today():
                raise serializers.ValidationError(
                    "Release date cannot be today. Please set a date later than today."
                )
            return value

        def validate_file(self, value: FileModel):
            request = self.context.get("request")
            if request and value.owner.id != request.user.id:
                raise serializers.ValidationError("You do not own the provided file.")
            return value

        def validate_film(self, value):
            request = self.context.get("request")
            if request and value and value.owner.id != request.user.id:
                raise serializers.ValidationError("You do not own the provided film.")
            return value

    class ShortRetrieve(serializers.ModelSerializer):
        owner = BaseUserSerializer()
        film = BaseFilmSerializer()

        class Meta:
            model = Short
            exclude = ["saved", "date_last_modified"]


class FilmPurchaseSerializer:
    class CreatePurchase(serializers.ModelSerializer):
        method = serializers.ChoiceField(choices=enums.PaymentType.choices())

        class Meta:
            model = Purchase
            fields = ["method"]


        def validate(self, attrs):
            user = self.context["request"].user
            film = self.context.get("film")

            if Purchase.objects.filter(
                owner=user,
                film=film, 
                payment_status=enums.PurchasePaymentStatus.COMPLETED.value,
                status=enums.PurchaseStatusType.ACTIVE.value
            ).exists():
                raise exceptions.CustomException(
                    message="User has already purchased this film."
                )

            return attrs

        def create(self, validated_data):
            user = self.context["request"].user
            film = self.context["film"]
            transaction = self.context["transaction"]

            purchase = Purchase.objects.create(
                owner=user, project=film, transaction=transaction
            )

            return purchase
    
    class FilmPurchaseResponse(serializers.Serializer):
        status = serializers.CharField(
            read_only=True, help_text=_("The status of the transfer")
        )
        data = serializers.DictField(
            read_only=True, help_text=_("The provider status and approval status of the transfer")
        )
        error = serializers.CharField(read_only=True)
        message = serializers.CharField(read_only=True)
    
    class RetrievePurchase(serializers.ModelSerializer):
        film = BaseFilmSerializer()
        owner = BaseUserSerializer()
        transaction_id = serializers.SerializerMethodField()

        class Meta:
            model = Purchase
            exclude = ["date_last_modified"]

        def get_transaction_id(self, obj):
            transaction = obj.transaction
            return transaction.reference