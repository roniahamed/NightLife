from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.events.models import Event, EventCategory, EventTicketTier, TicketPurchase, EventRSVP
from apps.venues.models import Venue
from decimal import Decimal
from unittest.mock import patch

User = get_user_model()

class TicketingAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create user
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='password123', first_name='Test', last_name='User')
        self.user.registration_type = 'user'
        self.user.save()
        self.client.force_authenticate(user=self.user)
        
        # Create venue owner
        self.owner = User.objects.create_user(username='venueowner', email='owner@example.com', password='password123', first_name='Venue', last_name='Owner')
        self.owner.registration_type = 'venue'
        self.owner.save()
        
        # Create venue
        self.venue = Venue.objects.create(
            owner=self.owner, name='Test Club', description='A club',
            address='123 Main St', is_approved=True, 
            stripe_account_id='acct_123', stripe_account_status='active'
        )
        self.owner.venue_profile = self.venue
        self.owner.save()
        
        # Create Event
        self.event = Event.objects.create(
            venue=self.venue, title='DJ Night', description='Night of fun',
            start_time='2030-01-01T20:00:00Z', end_time='2030-01-02T02:00:00Z'
        )
        
        # Create Ticket Tier
        self.tier = EventTicketTier.objects.create(
            event=self.event, name='General Admission', price=Decimal('20.00'),
            total_quantity=100
        )
        
    def test_list_ticket_types(self):
        url = reverse('ticket-types-list')
        response = self.client.get(url, {'event_id': str(self.event.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'General Admission')
        
    def test_rsvp(self):
        url = reverse('ticket-rsvp')
        response = self.client.post(url, {'event_id': str(self.event.id), 'is_going': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(EventRSVP.objects.filter(user=self.user, event=self.event).exists())
        
    @patch('stripe.PaymentIntent.create')
    def test_checkout(self, mock_pi_create):
        mock_pi_create.return_value = type('obj', (object,), {'id': 'pi_123', 'client_secret': 'secret_123'})()
        
        url = reverse('ticket-checkout')
        response = self.client.post(url, {'ticket_tier_id': str(self.tier.id), 'quantity': 2}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('client_secret', response.data['data'])
        self.assertIn('purchase_id', response.data['data'])
        
        purchase_id = response.data['data']['purchase_id']
        purchase = TicketPurchase.objects.get(id=purchase_id)
        self.assertEqual(purchase.quantity, 2)
        self.assertEqual(purchase.status, 'pending')
        
    def test_ticket_history(self):
        # Create a purchase first
        purchase = TicketPurchase.objects.create(
            user=self.user, event=self.event, ticket_tier=self.tier,
            quantity=1, total_amount=Decimal('21.00'), platform_fee=Decimal('1.00'),
            status='completed'
        )
        
        url = reverse('ticket-history')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], str(purchase.id))
        
    def test_get_ticket_qr(self):
        purchase = TicketPurchase.objects.create(
            user=self.user, event=self.event, ticket_tier=self.tier,
            quantity=1, total_amount=Decimal('21.00'), platform_fee=Decimal('1.00'),
            status='completed'
        )
        
        url = reverse('ticket-qr', kwargs={'pk': str(purchase.id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'image/png')
        
    @patch('stripe.Refund.create')
    def test_request_refund(self, mock_refund_create):
        mock_refund_create.return_value = type('obj', (object,), {'id': 're_123'})()
        
        purchase = TicketPurchase.objects.create(
            user=self.user, event=self.event, ticket_tier=self.tier,
            quantity=1, total_amount=Decimal('21.00'), platform_fee=Decimal('1.00'),
            status='completed', stripe_payment_intent_id='pi_123'
        )
        
        url = reverse('ticket-refund', kwargs={'pk': str(purchase.id)})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, 'refunded')
