from rest_framework import serializers
from .models import VenueMessage
from apps.events.models import Event

class EventMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'title', 'start_datetime', 'cover_image']

class VenueMessageSerializer(serializers.ModelSerializer):
    sender_venue_name = serializers.CharField(source='sender_venue.name', read_only=True)
    sender_venue_image = serializers.ImageField(source='sender_venue.cover_image', read_only=True)
    event_details = EventMinimalSerializer(source='event', read_only=True)

    class Meta:
        model = VenueMessage
        fields = [
            'id', 'sender_venue', 'sender_venue_name', 'sender_venue_image',
            'recipient_user', 'event', 'event_details', 'content', 'is_read', 'created_at'
        ]
        read_only_fields = ['id', 'sender_venue', 'is_read', 'created_at']

class VenueMessageCreateSerializer(serializers.Serializer):
    recipient_user_id = serializers.UUIDField(required=False, help_text="ID of the user to message. Required if broadcast_to_followers is false.")
    broadcast_to_followers = serializers.BooleanField(default=False, help_text="Set to true to message all venue followers.")
    event_id = serializers.UUIDField(required=False, allow_null=True)
    content = serializers.CharField()

    def validate(self, attrs):
        if not attrs.get('broadcast_to_followers') and not attrs.get('recipient_user_id'):
            raise serializers.ValidationError("Either recipient_user_id or broadcast_to_followers must be provided.")
        return attrs
