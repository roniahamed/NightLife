import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import stripe
from django.conf import settings
from apps.venues.models import Venue

def run_tests():
    stripe.api_key = settings.STRIPE_SECRET_KEY
    account = stripe.Account.retrieve('acct_1TqoZkAMDCuDRw9y')
    print(f"Details Submitted: {account.details_submitted}")
    print(f"Charges Enabled: {account.charges_enabled}")
    print(f"Capabilities: {account.capabilities}")
    
    venue = Venue.objects.filter(stripe_account_id='acct_1TqoZkAMDCuDRw9y').first()
    
    if account.charges_enabled:
        venue.stripe_account_status = 'active'
    elif account.details_submitted:
        venue.stripe_account_status = 'restricted'
    else:
        venue.stripe_account_status = 'pending'
    
    venue.save()
    print(f"Saved DB Status as: {venue.stripe_account_status}")

if __name__ == "__main__":
    run_tests()
