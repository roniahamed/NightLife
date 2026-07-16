from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EventViewSet, EventCategoryViewSet, EventRSVPView,
    EventTicketTierViewSet, TicketPurchaseViewSet, StripeWebhookView,
    EventLineupViewSet, TicketQRCodeView, TicketRefundView, TicketScanView
)

router = DefaultRouter()
router.register(r'categories', EventCategoryViewSet, basename='event-categories')
router.register(r'', EventViewSet, basename='events')

ticket_purchases_list = TicketPurchaseViewSet.as_view({
    'get': 'list',
    'post': 'create'
})
ticket_purchases_detail = TicketPurchaseViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

event_tickets_list = EventTicketTierViewSet.as_view({
    'get': 'list',
    'post': 'create'
})
event_tickets_detail = EventTicketTierViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

event_lineup_list = EventLineupViewSet.as_view({
    'get': 'list',
    'post': 'create'
})
event_lineup_detail = EventLineupViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

urlpatterns = [
    path('webhook/stripe/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('purchases/', ticket_purchases_list, name='ticket-purchases-list'),
    path('purchases/<str:pk>/', ticket_purchases_detail, name='ticket-purchases-detail'),
    path('purchases/<str:pk>/qr/', TicketQRCodeView.as_view(), name='ticket-qr-code'),
    path('purchases/<str:pk>/refund/', TicketRefundView.as_view(), name='ticket-refund'),
    path('purchases/<str:pk>/scan/', TicketScanView.as_view(), name='ticket-scan'),
    path('<str:event_pk>/tickets/', event_tickets_list, name='event-tickets-list'),
    path('<str:event_pk>/tickets/<str:pk>/', event_tickets_detail, name='event-tickets-detail'),
    path('<str:event_pk>/lineups/', event_lineup_list, name='event-lineups-list'),
    path('<str:event_pk>/lineups/<str:pk>/', event_lineup_detail, name='event-lineups-detail'),
    path('<str:pk>/rsvp/', EventRSVPView.as_view(), name='event-rsvp'),
    path('', include(router.urls)),
]
