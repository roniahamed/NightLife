from django.urls import path
from .views import (
    NotificationListView,
    MarkNotificationReadView,
    MarkAllNotificationsReadView,
    FCMDeviceCreateView
)

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification-list'),
    path('<int:pk>/read/', MarkNotificationReadView.as_view(), name='notification-read'),
    path('read-all/', MarkAllNotificationsReadView.as_view(), name='notification-read-all'),
    path('device/', FCMDeviceCreateView.as_view(), name='fcm-device-register'),
]
