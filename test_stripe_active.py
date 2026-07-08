import os
import django
import sys
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import stripe
from django.conf import settings
from apps.venues.models import Venue
from apps.events.models import Event, EventTicketTier
from apps.users.models import User
from apps.venues.services import generate_stripe_dashboard_link
from apps.events.services import create_ticket_purchase
from decimal import Decimal

def run_tests():
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    venue = Venue.objects.filter(stripe_account_id='acct_1TqoZkAMDCuDRw9y').first()
    if not venue:
        print("Could not find the Venue with acct_1TqoZkAMDCuDRw9y")
        return
        
    print(f"Venue Status in DB: {venue.stripe_account_status}")

    print("\n--- Testing Dashboard Link (Active Account) ---")
    try:
        dash_url = generate_stripe_dashboard_link(venue)
        print(f"SUCCESS: Dashboard URL generated: {dash_url}")
    except Exception as e:
        print(f"FAILED Dashboard Link: {e}")

    print("\n--- Testing Ticket Purchase with Transfers (Active Account) ---")
    event, _ = Event.objects.get_or_create(
        venue=venue, 
        title="Stripe Test Event", 
        defaults={
            'is_active': True,
            'start_time': timezone.now() + timedelta(days=1),
            'end_time': timezone.now() + timedelta(days=1, hours=4)
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
        print(f"SUCCESS: Payment Intent created WITH Destination Transfer!")
        print(f"Client Secret: {client_secret[:30]}...")
        print(f"Purchase ID: {purchase.id}")
        
        # Verify transfer logic in Stripe
        pi = stripe.PaymentIntent.retrieve(client_secret.split('_secret')[0])
        transfer_dest = pi.transfer_data.destination if pi.transfer_data else "None"
        print(f"Stripe Target Transfer Account: {transfer_dest}")
        
    except Exception as e:
        print(f"FAILED Ticket Purchase: {e}")

if __name__ == "__main__":
    run_tests()
