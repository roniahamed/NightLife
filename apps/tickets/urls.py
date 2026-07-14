from django.urls import path
from apps.events.views import (
    EventTicketTierViewSet, EventRSVPView, TicketPurchaseViewSet,
    TicketQRCodeView, TicketRefundView
)

ticket_types_list = EventTicketTierViewSet.as_view({'get': 'list'})
ticket_history_list = TicketPurchaseViewSet.as_view({'get': 'list'})
ticket_checkout = TicketPurchaseViewSet.as_view({'post': 'create'})

urlpatterns = [
    path('types/', ticket_types_list, name='ticket-types-list'),
    path('rsvp/', EventRSVPView.as_view(), name='ticket-rsvp'),
    path('checkout/', ticket_checkout, name='ticket-checkout'),
    path('history/', ticket_history_list, name='ticket-history'),
    path('<str:pk>/qr/', TicketQRCodeView.as_view(), name='ticket-qr'),
    path('<str:pk>/refund/', TicketRefundView.as_view(), name='ticket-refund'),
]
