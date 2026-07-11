from decimal import Decimal
from rest_framework.test import APITestCase
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
import datetime
from unittest.mock import patch
from .models import Event, EventCategory, EventRSVP, EventTicketTier, TicketPurchase, EventLineup
from apps.venues.models import Venue
import uuid

User = get_user_model()

class EventTests(APITestCase):

    def setUp(self):
        # User 1 - Venue Owner
        self.venue_user = User.objects.create_user(
            username='venueowner',
            email='venue@example.com',
            password='password123',
            registration_type='venue'
        )
        self.venue = Venue.objects.create(
            owner=self.venue_user,
            name='Test Club',
            is_approved=True,
            stripe_account_id='acct_test123',
            stripe_account_status='active'
        )
        
        # User 2 - Regular User
        self.regular_user = User.objects.create_user(
            username='regularuser',
            email='user@example.com',
            password='password123',
            registration_type='user'
        )
        
        self.category = EventCategory.objects.create(name='Live Music')

    def test_create_event_by_venue(self):
        self.client.force_authenticate(user=self.venue_user)
        # Generate token with active_profile='venue' manually isn't supported by force_authenticate,
        # but our fallback checks user.registration_type which is 'venue' so it works.
        url = reverse('events-list')
        data = {
            'title': 'Friday Night Party',
            'description': 'Come join us!',
            'start_time': timezone.now() + datetime.timedelta(days=2),
            'ticket_price': '20.00',
            'category_ids': [self.category.id]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Event.objects.first().venue, self.venue)

    def test_create_event_by_user_fails(self):
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('events-list')
        data = {
            'title': 'My Party',
            'description': 'Invalid party',
            'start_time': timezone.now() + datetime.timedelta(days=2),
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_event_with_nested_data(self):
        self.client.force_authenticate(user=self.venue_user)
        url = reverse('events-list')
        data = {
            'title': 'Nested Create Party',
            'description': 'Nested desc',
            'start_time': timezone.now() + datetime.timedelta(days=2),
            'ticket_price': '0.00',
            'ticket_tiers': [
                {'name': 'VIP', 'price': '50.00', 'total_quantity': 50, 'description': 'VIP desc'}
            ],
            'lineup': [
                {'artist_name': 'Artist 1', 'role': 'headliner'}
            ]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        event = Event.objects.get(title='Nested Create Party')
        self.assertEqual(event.ticket_tiers.count(), 1)
        self.assertEqual(event.lineup.count(), 1)
        self.assertEqual(event.ticket_tiers.first().name, 'VIP')
        self.assertEqual(event.lineup.first().artist_name, 'Artist 1')

    def test_update_event_with_nested_data(self):
        self.client.force_authenticate(user=self.venue_user)
        event = Event.objects.create(
            venue=self.venue,
            title='Update Party',
            start_time=timezone.now() + datetime.timedelta(days=2)
        )
        tier1 = EventTicketTier.objects.create(event=event, name='Tier 1', price='10.00', total_quantity=100)
        tier2 = EventTicketTier.objects.create(event=event, name='Tier 2', price='20.00', total_quantity=50)
        artist1 = EventLineup.objects.create(event=event, artist_name='Artist 1')
        artist2 = EventLineup.objects.create(event=event, artist_name='Artist 2')
        
        url = reverse('events-detail', kwargs={'pk': event.id})
        data = {
            'title': 'Updated Party',
            'ticket_tiers': [
                {'id': str(tier1.id), 'name': 'Tier 1 Updated', 'price': '15.00'}, 
                {'name': 'Tier 3', 'price': '30.00', 'total_quantity': 10} 
            ],
            'lineup': [
                {'id': str(artist1.id), 'artist_name': 'Artist 1 Updated'} 
            ],
            'remove_ticket_tier_ids': [str(tier2.id)], 
            'remove_lineup_ids': [str(artist2.id)] 
        }
        
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        event.refresh_from_db()
        self.assertEqual(event.title, 'Updated Party')
        
        self.assertEqual(event.ticket_tiers.count(), 2)
        self.assertTrue(event.ticket_tiers.filter(name='Tier 1 Updated').exists())
        self.assertTrue(event.ticket_tiers.filter(name='Tier 3').exists())
        self.assertFalse(event.ticket_tiers.filter(id=tier2.id).exists())
        
        self.assertEqual(event.lineup.count(), 1)
        self.assertTrue(event.lineup.filter(artist_name='Artist 1 Updated').exists())
        self.assertFalse(event.lineup.filter(id=artist2.id).exists())

    def test_rsvp_to_event(self):
        event = Event.objects.create(
            venue=self.venue,
            title='Test Event',
            description='Desc',
            start_time=timezone.now() + datetime.timedelta(days=1)
        )
        
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('event-rsvp', kwargs={'pk': event.id})
        
        # RSVP Going
        response = self.client.post(url, {'status': 'going'}, format='json')
        print(response.data); print(response.data); self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(EventRSVP.objects.filter(user=self.regular_user, event=event, status='going').exists())
        
        # RSVP Interested
        response = self.client.post(url, {'status': 'interested'}, format='json')
        print(response.data); print(response.data); self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(EventRSVP.objects.filter(user=self.regular_user, event=event, status='interested').exists())
        
        # Remove RSVP
        response = self.client.post(url, {'status': 'remove'}, format='json')
        print(response.data); print(response.data); self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(EventRSVP.objects.filter(user=self.regular_user, event=event).exists())


class TicketTests(APITestCase):
    def setUp(self):
        self.venue_user = User.objects.create_user(
            username='venueowner',
            email='venue@example.com',
            password='password123',
            registration_type='venue'
        )
        self.venue = Venue.objects.create(
            owner=self.venue_user,
            name='Test Club',
            is_approved=True,
            stripe_account_id='acct_test123'
        )
        
        self.regular_user = User.objects.create_user(
            username='regularuser',
            email='user@example.com',
            password='password123',
            registration_type='user'
        )
        
        self.event = Event.objects.create(
            venue=self.venue,
            title='Test Event',
            description='Desc',
            start_time=timezone.now() + datetime.timedelta(days=1)
        )

    def test_create_ticket_tier(self):
        self.client.force_authenticate(user=self.venue_user)
        url = reverse('event-tickets-list', kwargs={'event_pk': self.event.id})
        data = {
            'name': 'VIP',
            'price': '100.00',
            'total_quantity': 50
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(EventTicketTier.objects.count(), 1)

    def test_purchase_ticket_insufficient_quantity(self):
        tier = EventTicketTier.objects.create(
            event=self.event,
            name='Early Bird',
            price='20.00',
            total_quantity=5,
            sold_quantity=4
        )
        
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('ticket-purchases-list')
        data = {
            'ticket_tier_id': tier.id,
            'quantity': 2
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'Not enough tickets available.')

    @patch('stripe.PaymentIntent.create')
    def test_purchase_ticket_venue_not_onboarded(self, mock_stripe_create):
        mock_stripe_create.return_value = type('obj', (object,), {
            'id': 'pi_test_hold',
            'client_secret': 'secret_test_hold'
        })
        
        self.venue.stripe_account_id = None
        self.venue.save()
        
        tier = EventTicketTier.objects.create(
            event=self.event,
            name='General',
            price='10.00',
            total_quantity=100
        )
        
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('ticket-purchases-list')
        data = {
            'ticket_tier_id': tier.id,
            'quantity': 1
        }
        response = self.client.post(url, data, format='json')
        print(response.data); self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(TicketPurchase.objects.count(), 1)
        
        purchase = TicketPurchase.objects.first()
        self.assertFalse(purchase.funds_transferred_to_venue)
        self.assertEqual(purchase.stripe_payment_intent_id, 'pi_test_hold')
        
        # Verify transfer_data was NOT passed to stripe
        mock_stripe_create.assert_called_once()
        kwargs = mock_stripe_create.call_args.kwargs
        self.assertNotIn('transfer_data', kwargs)

    def test_create_ticket_tier_by_wrong_venue_owner(self):
        other_venue_owner = User.objects.create_user(
            username='otherowner',
            email='other@example.com',
            password='password123',
            registration_type='venue'
        )
        
        self.client.force_authenticate(user=other_venue_owner)
        url = reverse('event-tickets-list', kwargs={'event_pk': self.event.id})
        data = {
            'name': 'VIP',
            'price': '100.00',
            'total_quantity': 50
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    @patch('stripe.PaymentIntent.create')
    def test_purchase_ticket_success(self, mock_stripe_create):
        mock_stripe_create.return_value = type('obj', (object,), {
            'id': 'pi_test123',
            'client_secret': 'secret_test123'
        })
        
        tier = EventTicketTier.objects.create(
            event=self.event,
            name='General',
            price='50.00',
            total_quantity=100
        )
        
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('ticket-purchases-list')
        data = {
            'ticket_tier_id': tier.id,
            'quantity': 2
        }
        response = self.client.post(url, data, format='json')
        print(response.data); self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(TicketPurchase.objects.count(), 1)
        
        purchase = TicketPurchase.objects.first()
        self.assertEqual(purchase.quantity, 2)
        # 50 * 2 = 100 base ticket
        # 3% platform fee = 3
        # Total = (100 + 0.30) / (1 - 0.029) = 100.30 / 0.971 = 103.295... round to 103.30
        self.assertEqual(purchase.total_amount, Decimal('103.30'))
        self.assertEqual(purchase.platform_fee, Decimal('3.00'))
        self.assertEqual(purchase.stripe_payment_intent_id, 'pi_test123')
        self.assertEqual(purchase.status, 'pending')

    @patch('stripe.PaymentIntent.create')
    def test_purchase_ticket_insufficient_quantity(self, mock_stripe_create):
        mock_stripe_create.return_value = type('obj', (object,), {
            'id': 'pi_test123',
            'client_secret': 'secret_test123'
        })
        
        tier = EventTicketTier.objects.create(
            event=self.event,
            name='General',
            price='50.00',
            total_quantity=2
        )
        
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('ticket-purchases-list')
        
        # Buy 1 ticket (should succeed)
        response1 = self.client.post(url, {'ticket_tier_id': tier.id, 'quantity': 1}, format='json')
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # Try to buy 2 more tickets (should fail, only 1 left)
        response2 = self.client.post(url, {'ticket_tier_id': tier.id, 'quantity': 2}, format='json')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        
    @patch('stripe.PaymentIntent.create')
    def test_purchase_ticket_reservation_expiration(self, mock_stripe_create):
        mock_stripe_create.return_value = type('obj', (object,), {
            'id': 'pi_test123',
            'client_secret': 'secret_test123'
        })
        
        tier = EventTicketTier.objects.create(
            event=self.event,
            name='General',
            price='50.00',
            total_quantity=1
        )
        
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('ticket-purchases-list')
        
        # Buy 1 ticket
        self.client.post(url, {'ticket_tier_id': tier.id, 'quantity': 1}, format='json')
        
        # Manually backdate the created_at of the pending purchase to 6 minutes ago
        purchase = TicketPurchase.objects.first()
        purchase.created_at = timezone.now() - datetime.timedelta(minutes=6)
        purchase.save()
        
        # Try to buy the ticket again (should succeed because previous reservation expired)
        response = self.client.post(url, {'ticket_tier_id': tier.id, 'quantity': 1}, format='json')
        print(response.data); print(response.data); self.assertEqual(response.status_code, status.HTTP_200_OK)
