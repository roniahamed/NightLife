from django.urls import path
from .views import (
    SendVenueMessageView, 
    UserInboxView, 
    MarkMessageReadView, 
    MessageDetailView, 
    MarkAllMessagesReadView
)

urlpatterns = [
    path('venue/send/', SendVenueMessageView.as_view(), name='send-venue-message'),
    path('inbox/', UserInboxView.as_view(), name='user-inbox'),
    path('inbox/read-all/', MarkAllMessagesReadView.as_view(), name='mark-all-messages-read'),
    path('<str:pk>/', MessageDetailView.as_view(), name='message-detail'),
    path('<str:pk>/read/', MarkMessageReadView.as_view(), name='mark-message-read'),
]
