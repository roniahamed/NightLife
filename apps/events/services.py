from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
import stripe
from django.conf import settings
from .models import EventTicketTier, TicketPurchase, StripeWebhookEvent
from apps.venues.models import Venue

class TicketPurchaseError(Exception):
    pass

def create_ticket_purchase(user, tier_id, quantity):
    """
    Creates a ticket purchase with row-level locking and 5-minute reservation logic.
    Returns (purchase_instance, client_secret).
    """
    with transaction.atomic():
        try:
            tier = EventTicketTier.objects.select_for_update().get(pk=tier_id)
        except EventTicketTier.DoesNotExist:
            raise TicketPurchaseError("Ticket tier not found.")
            
        # Calculate active pending tickets (reserved in the last 5 minutes)
        active_pending_quantity = TicketPurchase.objects.filter(
            ticket_tier=tier,
            status='pending',
            created_at__gte=timezone.now() - timedelta(minutes=5)
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        if tier.sold_quantity + active_pending_quantity + quantity > tier.total_quantity:
            raise TicketPurchaseError("Not enough tickets available.")
            
        # Calculate platform target profit based on global Site Settings
        from apps.common.models import PlatformSettings
        from decimal import Decimal, ROUND_HALF_UP
        
        event = tier.event
        venue = event.venue
        
        # Base ticket amount set by the venue
        base_ticket_amount = tier.price * quantity
        base_ticket_decimal = Decimal(str(base_ticket_amount))
        
        # Calculate platform fee (deducted from the base ticket / venue payout)
        from apps.common.models import PlatformSettings
        from decimal import Decimal, ROUND_HALF_UP
        
        settings_obj, _ = PlatformSettings.objects.get_or_create(id=1)
        fee_percentage = Decimal(str(settings_obj.ticket_commission_percentage)) / Decimal('100')
        platform_fee = base_ticket_decimal * fee_percentage
        
        # Auto-calculate total charge to customer to cover ONLY Stripe's 2.9% + 30 cents fee
        # Formula: Total = (Base Ticket + $0.30) / (1 - 0.029)
        # This ensures exactly `base_ticket_decimal` remains after Stripe takes its cut.
        numerator = base_ticket_decimal + Decimal('0.30')
        denominator = Decimal('1') - Decimal('0.029')
        total_customer_charge = (numerator / denominator).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        purchase = TicketPurchase.objects.create(
            user=user,
            event=event,
            ticket_tier=tier,
            quantity=quantity,
            total_amount=total_customer_charge,
            platform_fee=platform_fee,
            funds_transferred_to_venue=False
        )
        
    try:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        intent_kwargs = {
            'amount': int(total_customer_charge * 100),
            'currency': 'usd',
            'metadata': {
                'purchase_id': str(purchase.id),
                'event_id': str(event.id),
                'user_id': str(user.id)
            }
        }
        
        # Use Stripe Connect if venue has a connected account
        if venue.stripe_account_id and venue.stripe_account_status == 'active':
            # Transfer base_ticket_amount minus platform_fee to the venue
            amount_for_venue = int((base_ticket_decimal - platform_fee) * 100)
            intent_kwargs['transfer_data'] = {
                'destination': venue.stripe_account_id,
                'amount': amount_for_venue,
            }
            
        payment_intent = stripe.PaymentIntent.create(**intent_kwargs)
        
        purchase.stripe_payment_intent_id = payment_intent.id
        purchase.save()
        
        return purchase, payment_intent.client_secret
        
    except stripe.error.StripeError as e:
        purchase.status = 'failed'
        purchase.save()
        raise TicketPurchaseError(str(e))

def handle_stripe_webhook_event(payload, sig_header):
    """
    Handles Stripe webhooks (payment updates, connect account updates).
    Returns a status code integer.
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return 400
    except stripe.error.SignatureVerificationError:
        return 400
        
    # Idempotency Check
    if StripeWebhookEvent.objects.filter(stripe_event_id=event.id).exists():
        return 200
    
    StripeWebhookEvent.objects.create(stripe_event_id=event.id, type=event.type)
        
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
                
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        purchase_id = payment_intent.get('metadata', {}).get('purchase_id')
        if purchase_id:
            try:
                purchase = TicketPurchase.objects.get(id=purchase_id)
                purchase.status = 'failed'
                purchase.save()
            except TicketPurchase.DoesNotExist:
                pass
                
    elif event['type'] == 'account.updated':
        account = event['data']['object']
        try:
            venue = Venue.objects.get(stripe_account_id=account.id)
            if account.charges_enabled:
                venue.stripe_account_status = 'active'
            elif account.details_submitted:
                venue.stripe_account_status = 'restricted'
            else:
                venue.stripe_account_status = 'pending'
            venue.save()
        except Venue.DoesNotExist:
            pass
            
    elif event['type'] == 'account.application.deauthorized':
        account_id = event.get('account') or (event['data']['object'].id if 'object' in event['data'] else None)
        if account_id:
            try:
                venue = Venue.objects.get(stripe_account_id=account_id)
                venue.stripe_account_status = 'disconnected'
                venue.save()
            except Venue.DoesNotExist:
                pass
                
    return 200
