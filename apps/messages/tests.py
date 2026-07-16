from rest_framework.test import APITestCase
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.venues.models import Venue
from apps.users.models import UserFollow
from .models import VenueMessage
from unittest.mock import patch

User = get_user_model()

class MockAuthVenue:
    payload = {'active_profile': 'venue'}

class MockAuthStandard:
    payload = {'active_profile': 'standard'}

class VenueMessagingTests(APITestCase):
    def setUp(self):
        # Create venue owner
        self.venue_owner = User.objects.create_user(
            email='venue@test.com',
            username='venueowner',
            password='password123',
            registration_type='venue'
        )
        self.venue = Venue.objects.create(
            owner=self.venue_owner,
            name='Test Venue'
        )
        
        # Create standard users
        self.user1 = User.objects.create_user(
            email='user1@test.com',
            username='user1',
            password='password123',
            registration_type='standard'
        )
        self.user2 = User.objects.create_user(
            email='user2@test.com',
            username='user2',
            password='password123',
            registration_type='standard'
        )
        
        # user1 follows the venue
        from apps.venues.models import VenueFollow
        VenueFollow.objects.create(user=self.user1, venue=self.venue)

        self.send_url = reverse('send-venue-message')
        self.inbox_url = reverse('user-inbox')

    @patch('apps.messages.services.send_user_notification')
    def test_send_message_to_specific_user(self, mock_send_notification):
        self.client.force_authenticate(user=self.venue_owner, token=MockAuthVenue())
        
        data = {
            'recipient_user_id': self.user2.id,
            'content': 'Hello user 2!'
        }
        
        response = self.client.post(self.send_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(VenueMessage.objects.count(), 1)
        self.assertEqual(VenueMessage.objects.first().recipient_user, self.user2)
        mock_send_notification.assert_called_once()

    @patch('apps.messages.services.send_user_notification')
    def test_send_message_broadcast(self, mock_send_notification):
        self.client.force_authenticate(user=self.venue_owner, token=MockAuthVenue())
        
        data = {
            'broadcast_to_followers': True,
            'content': 'Hello all followers!'
        }
        
        response = self.client.post(self.send_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(VenueMessage.objects.count(), 1)
        self.assertEqual(VenueMessage.objects.first().recipient_user, self.user1)
        mock_send_notification.assert_called_once()

    def test_send_message_permission_denied_for_standard_user(self):
        self.client.force_authenticate(user=self.user1, token=MockAuthStandard())
        
        data = {
            'recipient_user_id': self.user2.id,
            'content': 'Hello user 2!'
        }
        
        response = self.client.post(self.send_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_inbox_and_read(self):
        # Create a message for user1
        msg = VenueMessage.objects.create(
            sender_venue=self.venue,
            recipient_user=self.user1,
            content="Test inbox message"
        )
        
        self.client.force_authenticate(user=self.user1, token=MockAuthStandard())
        
        # Test Inbox
        response = self.client.get(self.inbox_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertFalse(response.data['results'][0]['is_read'])
        
        # Test Mark as read
        read_url = reverse('mark-message-read', kwargs={'pk': msg.id})
        response = self.client.patch(read_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['data']['is_read'])
        
        # Verify in DB
        msg.refresh_from_db()
        self.assertTrue(msg.is_read)
