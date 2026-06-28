from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema

from django.conf import settings
from .models import EventCategory, Event, EventRSVP, EventTicketTier, TicketPurchase
from .serializers import (
    EventCategorySerializer, EventSerializer, EventRSVPSerializer,
    EventTicketTierSerializer, TicketPurchaseSerializer
)
from apps.common.permissions import IsActiveProfileUser, IsActiveProfileVenue
from apps.common.pagination import StandardResultsSetPagination
from apps.common.utils import success_response, error_response
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

class EventCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EventCategory.objects.all()
    serializer_class = EventCategorySerializer
    permission_classes = [permissions.AllowAny]

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

    @extend_schema(summary="RSVP to Event", description="RSVP to an event. Requires active_profile='user'. Status can be 'going' or 'interested' or 'remove'.", tags=['Events'])
    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        status_req = request.data.get('status')
        
        if status_req == 'remove':
            EventRSVP.objects.filter(user=request.user, event=event).delete()
            return success_response(message="RSVP removed successfully.")
            
        if status_req not in ['going', 'interested']:
            return error_response(message="Invalid status. Must be 'going', 'interested', or 'remove'.", status=status.HTTP_400_BAD_REQUEST)
            
        rsvp, created = EventRSVP.objects.update_or_create(
            user=request.user, 
            event=event,
            defaults={'status': status_req}
        )
        
        
        return success_response(message=f"RSVP updated to {status_req} successfully.")

class EventTicketTierViewSet(viewsets.ModelViewSet):
    serializer_class = EventTicketTierSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsActiveProfileVenue()]
        return [permissions.AllowAny()]
        
    def get_queryset(self):
        return EventTicketTier.objects.filter(event_id=self.kwargs.get('event_pk'))
        
    def perform_create(self, serializer):
        event = get_object_or_404(Event, pk=self.kwargs.get('event_pk'))
        if event.venue.owner != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only create tickets for your own events.")
        serializer.save(event=event)

class TicketPurchaseViewSet(viewsets.ModelViewSet):
    serializer_class = TicketPurchaseSerializer
    permission_classes = [permissions.IsAuthenticated, IsActiveProfileUser]
    
    def get_queryset(self):
        return TicketPurchase.objects.filter(user=self.request.user)
        
    @extend_schema(summary="Purchase Ticket", description="Creates a Stripe Payment Intent to purchase a ticket.")
    def create(self, request, *args, **kwargs):
        tier_id = request.data.get('ticket_tier_id')
        quantity = int(request.data.get('quantity', 1))
        
        tier = get_object_or_404(EventTicketTier, pk=tier_id)
        
        if tier.sold_quantity + quantity > tier.total_quantity:
            return error_response(message="Not enough tickets available.", status=status.HTTP_400_BAD_REQUEST)
            
        event = tier.event
        venue = event.venue
        
        total_amount = tier.price * quantity
        # Calculate platform fee (e.g. 10%)
        fee_percentage = getattr(settings, 'APPLICATION_FEE_PERCENTAGE', 10)
        platform_fee = (total_amount * fee_percentage) / 100
        
        funds_transferred = False
        
        purchase = TicketPurchase.objects.create(
            user=request.user,
            event=event,
            ticket_tier=tier,
            quantity=quantity,
            total_amount=total_amount,
            platform_fee=platform_fee,
            funds_transferred_to_venue=False
        )
        
        try:
            intent_kwargs = {
                'amount': int(total_amount * 100),
                'currency': 'usd',
                'payment_method_types': ['card'],
                'metadata': {
                    'purchase_id': str(purchase.id),
                    'user_id': str(request.user.id),
                    'event_id': str(event.id)
                }
            }
            
            if venue.stripe_account_id:
                intent_kwargs['application_fee_amount'] = int(platform_fee * 100)
                intent_kwargs['transfer_data'] = {
                    'destination': venue.stripe_account_id,
                }
                # Track that Stripe will auto-transfer this on success
                purchase.funds_transferred_to_venue = True 
                
            # Create Stripe PaymentIntent
            intent = stripe.PaymentIntent.create(**intent_kwargs)
            
            purchase.stripe_payment_intent_id = intent.id
            purchase.save()
            
            return success_response(data={
                'client_secret': intent.client_secret,
                'purchase_id': purchase.id,
                'total_amount': total_amount
            }, status=status.HTTP_201_CREATED)
            
        except stripe.error.StripeError as e:
            purchase.status = 'failed'
            purchase.save()
            return error_response(message=str(e), status=status.HTTP_400_BAD_REQUEST)

class StripeWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)
            
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            purchase_id = payment_intent.get('metadata', {}).get('purchase_id')
            
            if purchase_id:
                try:
                    purchase = TicketPurchase.objects.get(id=purchase_id)
                    purchase.status = 'completed'
                    purchase.save()
                    
                    # Update sold quantity
                    tier = purchase.ticket_tier
                    tier.sold_quantity += purchase.quantity
                    tier.save()
                    
                except TicketPurchase.DoesNotExist:
                    pass
                    
        return Response(status=status.HTTP_200_OK)
