from rest_framework import views, status, generics
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django.contrib.auth import get_user_model

from apps.common.permissions import IsActiveProfileVenue
from rest_framework.permissions import IsAuthenticated
from .models import VenueMessage
from .serializers import VenueMessageSerializer, VenueMessageCreateSerializer
from .services import process_and_send_venue_message, mark_message_as_read, mark_all_messages_as_read

User = get_user_model()

class SendVenueMessageView(views.APIView):
    permission_classes = [IsAuthenticated, IsActiveProfileVenue]

    @extend_schema(
        summary="Send Venue Message",
        description="Allows a venue to send a direct message to a specific user or broadcast to all followers.",
        request=VenueMessageCreateSerializer,
        responses={201: VenueMessageSerializer(many=True)},
        tags=['Venue Messaging']
    )
    def post(self, request, *args, **kwargs):
        serializer = VenueMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Send messages via service (Handles DB, Firebase, WebSockets, and all validations)
        serialized_data = process_and_send_venue_message(request.user, serializer.validated_data)

        return Response({
            "status": "success",
            "message": f"Successfully sent {len(serialized_data)} message(s).",
            "data": serialized_data
        }, status=status.HTTP_201_CREATED)


class UserInboxView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = VenueMessageSerializer

    @extend_schema(
        summary="User Inbox",
        description="Retrieve all messages sent to the authenticated user.",
        tags=['Venue Messaging']
    )
    def get_queryset(self):
        return VenueMessage.objects.filter(recipient_user=self.request.user).order_by('-created_at')

class MarkMessageReadView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Mark Message as Read",
        description="Marks a specific venue message as read.",
        responses={200: VenueMessageSerializer},
        tags=['Venue Messaging']
    )
    def patch(self, request, pk):
        serialized_data = mark_message_as_read(request.user, pk)
        
        return Response({
            "status": "success",
            "message": "Message marked as read.",
            "data": serialized_data
        }, status=status.HTTP_200_OK)

class MessageDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = VenueMessageSerializer

    @extend_schema(
        summary="Get Single Message",
        description="Retrieves a specific message and automatically marks it as read.",
        tags=['Venue Messaging']
    )
    def get_queryset(self):
        return VenueMessage.objects.filter(recipient_user=self.request.user)

    def get_object(self):
        obj = super().get_object()
        if not obj.is_read:
            obj.is_read = True
            obj.save()
        return obj

class MarkAllMessagesReadView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Mark All Messages Read",
        description="Marks all unread messages for the authenticated user as read.",
        tags=['Venue Messaging']
    )
    def post(self, request, *args, **kwargs):
        updated_count = mark_all_messages_as_read(request.user)
        return Response({
            "status": "success",
            "message": f"Successfully marked {updated_count} message(s) as read."
        }, status=status.HTTP_200_OK)
