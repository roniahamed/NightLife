from django.contrib.auth import get_user_model
from rest_framework.exceptions import NotFound, ValidationError
from apps.venues.models import Venue, VenueFollow
from apps.events.models import Event
from .models import VenueMessage
from .serializers import VenueMessageSerializer
from apps.notifications.firebase import send_user_notification
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

User = get_user_model()

def process_and_send_venue_message(user, data):
    """
    Validates recipients and event data, then sends the messages.
    """
    recipient_user_id = data.get('recipient_user_id')
    broadcast = data.get('broadcast_to_followers', False)
    event_id = data.get('event_id')
    content = data.get('content')

    try:
        venue = Venue.objects.get(owner=user)
    except Venue.DoesNotExist:
        raise NotFound("Venue profile not found.")

    event = None
    if event_id:
        try:
            event = Event.objects.get(id=event_id, venue=venue)
        except Event.DoesNotExist:
            raise NotFound("Event not found or does not belong to this venue.")

    recipients = []
    if broadcast:
        followers = VenueFollow.objects.filter(venue=venue).select_related('user')
        recipients = [f.user for f in followers]
    elif recipient_user_id:
        try:
            recipient_user = User.objects.get(id=recipient_user_id)
            recipients = [recipient_user]
        except User.DoesNotExist:
            raise NotFound("Recipient user not found.")

    if not recipients:
        raise ValidationError("No recipients found.")

    return send_venue_messages(venue, recipients, content, event)


def send_venue_messages(venue, recipients, content, event=None):
    """
    Creates VenueMessages, triggers Firebase push notifications, 
    and broadcasts to WebSockets for real-time delivery.
    """
    created_messages = []
    
    # 1. Save messages to DB & Send Push Notifications
    for user in recipients:
        msg = VenueMessage.objects.create(
            sender_venue=venue,
            recipient_user=user,
            event=event,
            content=content
        )
        created_messages.append(msg)

        send_user_notification(
            user=user,
            title=f"New Message from {venue.name}",
            message=content[:100] + "..." if len(content) > 100 else content,
            notification_type='venue_message',
            related_object_id=str(msg.id),
            data={'venue_id': str(venue.id)}
        )

    # 2. Serialize and Broadcast via WebSockets
    if created_messages:
        response_serializer = VenueMessageSerializer(created_messages, many=True)
        channel_layer = get_channel_layer()
        
        for msg_data in response_serializer.data:
            recipient_id = msg_data['recipient_user']
            async_to_sync(channel_layer.group_send)(
                f"user_inbox_{recipient_id}",
                {
                    'type': 'venue_message',
                    'message': msg_data
                }
            )
            
        return response_serializer.data
    
    return []


def mark_message_as_read(user, message_id):
    """
    Marks a specific message as read for the user.
    """
    try:
        message = VenueMessage.objects.get(id=message_id, recipient_user=user)
    except VenueMessage.DoesNotExist:
        raise NotFound("Message not found.")
        
    message.is_read = True
    message.save()
    return VenueMessageSerializer(message).data

def mark_all_messages_as_read(user):
    """
    Marks all unread messages as read for the user.
    """
    unread_messages = VenueMessage.objects.filter(recipient_user=user, is_read=False)
    updated_count = unread_messages.update(is_read=True)
    return updated_count
