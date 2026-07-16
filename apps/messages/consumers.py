import json
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model
from .services import mark_message_as_read

User = get_user_model()

@database_sync_to_async
def get_user_from_token(token):
    try:
        access_token = AccessToken(token)
        user = User.objects.get(id=access_token['user_id'])
        return user
    except Exception:
        return AnonymousUser()

class UserInboxConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        query_string = self.scope['query_string'].decode()
        query_params = parse_qs(query_string)
        
        token = query_params.get('token', [None])[0]
        if token:
            self.user = await get_user_from_token(token)
        else:
            self.user = AnonymousUser()

        if self.user.is_anonymous:
            await self.close()
            return

        self.group_name = f"user_inbox_{self.user.id}"

        # Join the user's specific inbox group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            # Leave room group
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    # Receive message from WebSocket (Client sending up, e.g. typing or read receipts)
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'seen':
                message_id = data.get('message_id')
                if message_id:
                    # Mark message as read in DB using sync_to_async
                    await database_sync_to_async(mark_message_as_read)(self.user, message_id)
                    
                    # Optionally notify the client that it was marked successfully
                    await self.send(text_data=json.dumps({
                        'type': 'message_seen_ack',
                        'message_id': message_id
                    }))
        except Exception as e:
            # Silently ignore or log parsing errors/not found errors
            pass

    # Receive message from room group (Sent by views.py)
    async def venue_message(self, event):
        message_data = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'data': message_data
        }))
