import os
import django
import sys
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import stripe
from django.conf import settings
from apps.users.models import User
from apps.venues.models import Venue
from apps.events.models import Event, EventTicketTier
from apps.common.models import PlatformSettings
from apps.venues.services import create_stripe_onboarding, generate_stripe_dashboard_link
from apps.events.services import create_ticket_purchase
from decimal import Decimal

def run_tests():
    stripe.api_key = settings.STRIPE_SECRET_KEY
    print(f"Using Stripe Key: {stripe.api_key[:10]}...")
    
    # 1. Test PlatformSettings
    PlatformSettings.objects.get_or_create(id=1, defaults={'ticket_commission_percentage': Decimal('3.00')})

    # 2. Get or create user and venue
    user, _ = User.objects.get_or_create(email="testowner@example.com", username="testowner")
    venue, _ = Venue.objects.get_or_create(owner=user, name="Stripe Test Venue", is_approved=True)

    print("\n--- Testing Stripe Connect Onboarding ---")
    try:
        url = create_stripe_onboarding(venue, "http://localhost/refresh", "http://localhost/return")
        print(f"SUCCESS: Onboarding URL generated: {url}")
        print(f"Stripe Account ID: {venue.stripe_account_id}")
    except Exception as e:
        print(f"FAILED Onboarding: {e}")

    # Simulate activating the account for testing purposes
    venue.stripe_account_status = 'pending'
    venue.save()

    print("\n--- Testing Dashboard Link ---")
    try:
        dash_url = generate_stripe_dashboard_link(venue)
        print(f"SUCCESS: Dashboard URL generated: {dash_url}")
    except Exception as e:
        print(f"EXPECTED FAILURE for Dashboard Link (Needs onboarding completion): {e}")

    print("\n--- Testing Ticket Purchase (Payment Intent) ---")
    now = timezone.now()
    event, _ = Event.objects.get_or_create(
        venue=venue, 
        title="Stripe Test Event", 
        defaults={
            'is_active': True,
            'start_time': now + timedelta(days=1),
            'end_time': now + timedelta(days=1, hours=4)
        }
    )
    tier, _ = EventTicketTier.objects.get_or_create(
        event=event, 
        name="VIP", 
        defaults={
            'price': Decimal('100.00'), 
            'total_quantity': 100
        }
    )
    
    buyer, _ = User.objects.get_or_create(email="buyer@example.com", username="buyer")
    
    try:
        purchase, client_secret = create_ticket_purchase(buyer, tier.id, 2)
        print(f"SUCCESS: Payment Intent created!")
        print(f"Client Secret: {client_secret[:30]}...")
        print(f"Purchase ID: {purchase.id}")
        print(f"Total Charged to User: ${purchase.total_amount}")
        print(f"Platform Fee (Commission): ${purchase.platform_fee}")
    except Exception as e:
        print(f"FAILED Ticket Purchase: {e}")

if __name__ == "__main__":
    run_tests()
