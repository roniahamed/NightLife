from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers as rf_serializers

from django.conf import settings
from .models import (
    EventCategory, Event, EventRSVP, EventTicketTier, TicketPurchase,
    EventLineup
)
from .serializers import (
    EventCategorySerializer, EventSerializer, 
    EventRSVPSerializer, EventTicketTierSerializer, TicketPurchaseSerializer,
    EventLineupSerializer
)
from apps.common.permissions import IsActiveProfileUser, IsActiveProfileVenue
from apps.common.pagination import StandardResultsSetPagination
from apps.common.utils import success_response, error_response
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

@extend_schema_view(
    list=extend_schema(tags=['Event Categories']),
    retrieve=extend_schema(tags=['Event Categories']),
)
class EventCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EventCategory.objects.all()
    serializer_class = EventCategorySerializer
    permission_classes = [permissions.AllowAny]

@extend_schema_view(
    list=extend_schema(tags=['Events']),
    retrieve=extend_schema(tags=['Events']),
    create=extend_schema(tags=['Events']),
    update=extend_schema(tags=['Events']),
    partial_update=extend_schema(tags=['Events']),
    destroy=extend_schema(tags=['Events']),
)
class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsActiveProfileVenue()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        queryset = Event.objects.filter(is_active=True).select_related('venue')
        
        # Filter by upcoming
        upcoming = self.request.query_params.get('upcoming')
        if upcoming == 'true':
            queryset = queryset.filter(start_time__gte=timezone.now())
            
        # Filter by venue
        venue_id = self.request.query_params.get('venue')
        if venue_id:
            queryset = queryset.filter(venue_id=venue_id)
            
        return queryset

    @extend_schema(summary="Create Event", description="Creates an event. Requires active_profile='venue'.", tags=['Events'])
    def perform_create(self, serializer):
        user = self.request.user
        if not hasattr(user, 'venue_profile'):
            from rest_framework.exceptions import ValidationError
            raise ValidationError("You do not have a venue profile.")
        if not user.venue_profile.is_approved:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Your venue must be approved by an admin before you can create events.")
            
        if not user.venue_profile.stripe_account_id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("You must connect a Stripe account before you can create events.")
            
        serializer.save(venue=user.venue_profile)

    def perform_update(self, serializer):
        if serializer.instance.venue.owner != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only edit events for your own venue.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.venue.owner != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only delete events for your own venue.")
        instance.delete()

class EventRSVPView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActiveProfileUser]

    @extend_schema(
        summary="RSVP to Event", 
        description="RSVP to an event. Requires active_profile='user'. Pass is_going: true to RSVP, false to remove.", 
        tags=['Events'],
        request=inline_serializer(name='EventRSVPRequest', fields={'is_going': rf_serializers.BooleanField()}),
        responses={200: OpenApiTypes.OBJECT}
    )
    def post(self, request, pk=None):
        event_id = pk or request.data.get('event_id')
        event = get_object_or_404(Event, pk=event_id)
        is_going = request.data.get('is_going')
        
        if is_going is None:
             return error_response(message="'is_going' boolean field is required.", status=status.HTTP_400_BAD_REQUEST)
             
        if is_going:
            EventRSVP.objects.get_or_create(user=request.user, event=event)
            return success_response(message="RSVP added successfully.")
        else:
            EventRSVP.objects.filter(user=request.user, event=event).delete()
            return success_response(message="RSVP removed successfully.")

@extend_schema_view(
    list=extend_schema(tags=['Event Tickets']),
    retrieve=extend_schema(tags=['Event Tickets']),
    create=extend_schema(tags=['Event Tickets']),
    update=extend_schema(tags=['Event Tickets']),
    partial_update=extend_schema(tags=['Event Tickets']),
    destroy=extend_schema(tags=['Event Tickets']),
)
class EventTicketTierViewSet(viewsets.ModelViewSet):
    serializer_class = EventTicketTierSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsActiveProfileVenue()]
        return [permissions.AllowAny()]
        
    def get_queryset(self):
        event_id = self.kwargs.get('event_pk') or self.request.query_params.get('event_id')
        if event_id:
            return EventTicketTier.objects.filter(event_id=event_id)
        return EventTicketTier.objects.all()
        
    def perform_create(self, serializer):
        event_id = self.kwargs.get('event_pk') or self.request.data.get('event_id')
        event = get_object_or_404(Event, pk=event_id)
        if event.venue.owner != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only create tickets for your own events.")
        serializer.save(event=event)

@extend_schema_view(
    list=extend_schema(tags=['Event Lineup']),
    retrieve=extend_schema(tags=['Event Lineup']),
    create=extend_schema(tags=['Event Lineup']),
    update=extend_schema(tags=['Event Lineup']),
    partial_update=extend_schema(tags=['Event Lineup']),
    destroy=extend_schema(tags=['Event Lineup']),
)
class EventLineupViewSet(viewsets.ModelViewSet):
    serializer_class = EventLineupSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsActiveProfileVenue()]
        return [permissions.AllowAny()]
        
    def get_queryset(self):
        return EventLineup.objects.filter(event_id=self.kwargs.get('event_pk'))
        
    def perform_create(self, serializer):
        event = get_object_or_404(Event, pk=self.kwargs.get('event_pk'))
        if event.venue.owner != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only add lineup for your own events.")
        serializer.save(event=event)

@extend_schema_view(
    list=extend_schema(tags=['Event Tickets']),
    retrieve=extend_schema(tags=['Event Tickets']),
    update=extend_schema(tags=['Event Tickets']),
    partial_update=extend_schema(tags=['Event Tickets']),
    destroy=extend_schema(tags=['Event Tickets']),
)
class TicketPurchaseViewSet(viewsets.ModelViewSet):
    serializer_class = TicketPurchaseSerializer
    permission_classes = [permissions.IsAuthenticated, IsActiveProfileUser]
    
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return TicketPurchase.objects.none()
        return TicketPurchase.objects.filter(user=self.request.user)
        
    @extend_schema(summary="Purchase Ticket", description="Creates a Stripe Payment Intent to purchase a ticket.", tags=['Event Tickets'])
    def create(self, request, *args, **kwargs):
        tier_id = request.data.get('ticket_tier_id')
        quantity = int(request.data.get('quantity', 1))
        
        from .services import create_ticket_purchase, TicketPurchaseError
        
        try:
            purchase, client_secret = create_ticket_purchase(request.user, tier_id, quantity)
            return success_response(data={
                "client_secret": client_secret,
                "purchase_id": str(purchase.id)
            })
        except TicketPurchaseError as e:
            return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return error_response(message=str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StripeWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(summary="Stripe Webhook", description="Webhook handler for Stripe payment events.", request=None, responses={200: OpenApiTypes.OBJECT}, tags=['Stripe Integration'])
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        
        from .services import handle_stripe_webhook_event
        
        status_code = handle_stripe_webhook_event(payload, sig_header)
        return Response(status=status_code)

class TicketQRCodeView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActiveProfileUser]
    
    @extend_schema(summary="Get Ticket QR Code", description="Returns the QR code image for a purchased ticket.", responses={200: OpenApiTypes.BINARY}, tags=['Event Tickets'])
    def get(self, request, pk):
        from .services import generate_ticket_qr
        purchase = get_object_or_404(TicketPurchase, pk=pk, user=request.user)
        qr_bytes = generate_ticket_qr(purchase.id)
        
        from django.http import HttpResponse
        return HttpResponse(qr_bytes, content_type="image/png")

class TicketRefundView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActiveProfileUser]
    
    @extend_schema(summary="Request Ticket Refund", description="Requests a refund for a ticket purchase.", responses={200: OpenApiTypes.OBJECT}, tags=['Event Tickets'])
    def post(self, request, pk):
        from .services import request_ticket_refund, TicketPurchaseError
        
        try:
            purchase = request_ticket_refund(request.user, pk)
            return success_response(message="Refund processed successfully.")
        except TicketPurchaseError as e:
            return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return error_response(message=str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

