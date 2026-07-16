from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import Notification
from .serializers import NotificationSerializer, FCMDeviceSerializer


class NotificationListView(generics.ListAPIView):
    """
    List all notifications for the authenticated user.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class MarkNotificationReadView(APIView):
    """
    Mark a specific notification as read.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: OpenApiResponse(description="Notification marked as read")}
    )
    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.is_read = True
        notification.save()
        return Response({'status': 'success', 'message': 'Notification marked as read'})


class MarkAllNotificationsReadView(APIView):
    """
    Mark all unread notifications as read for the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: OpenApiResponse(description="All notifications marked as read")}
    )
    def post(self, request):
        updated_count = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({
            'status': 'success', 
            'message': f'{updated_count} notifications marked as read'
        })


class FCMDeviceCreateView(generics.CreateAPIView):
    """
    Register a new FCM device token for the user.
    """
    serializer_class = FCMDeviceSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {'status': 'success', 'message': 'Device registered successfully', 'data': serializer.data},
            status=status.HTTP_201_CREATED, 
            headers=headers
        )
