from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EventViewSet, EventCategoryViewSet, EventRSVPView,
    EventTicketTierViewSet, TicketPurchaseViewSet, StripeWebhookView
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

urlpatterns = [
    path('webhook/stripe/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('purchases/', ticket_purchases_list, name='ticket-purchases-list'),
    path('purchases/<str:pk>/', ticket_purchases_detail, name='ticket-purchases-detail'),
    path('<str:event_pk>/tickets/', event_tickets_list, name='event-tickets-list'),
    path('<str:event_pk>/tickets/<str:pk>/', event_tickets_detail, name='event-tickets-detail'),
    path('<str:pk>/rsvp/', EventRSVPView.as_view(), name='event-rsvp'),
    path('', include(router.urls)),
]
