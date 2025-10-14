from rest_framework import serializers
from .models import WebhookEndpoint


class WebhookEndpointSerializer:

    class WebhookListCreate(serializers.ModelSerializer):
        secret_key = serializers.CharField(required=True, write_only=True)
            
        class Meta:
            model = WebhookEndpoint
            exclude = [
                "secret_encrypted",
                "failure_count", 
                "last_response_code", 
                "last_error", 
                "last_sent_at", 
                "date_last_modified"
            ]
            read_only_fields = ["id", "date_added"]

        
        def save(self, validated_data):
            secret_key = validated_data.pop("secret_key")
            webhook_endpoint = WebhookEndpoint(**validated_data)
            webhook_endpoint.set_secret(secret_key)
            webhook_endpoint.save()
            return webhook_endpoint
    
    class WebhookUpdate(serializers.ModelSerializer):
        secret_key = serializers.CharField(required=False, write_only=True)
            
        class Meta:
            model = WebhookEndpoint
            exclude = [
                "secret_encrypted",
                "failure_count", 
                "last_response_code", 
                "last_error", 
                "last_sent_at", 
                "date_last_modified"
            ]
            read_only_fields = ["id", "date_added"]
        
        def update(self, instance, validated_data):
            secret_key = validated_data.pop("secret", None)
            for k, v in validated_data.items():
                setattr(instance, k, v)
            if secret_key:
                instance.set_secret(secret_key)
            instance.save()
            return instance

