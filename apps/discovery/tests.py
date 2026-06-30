from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.utils import timezone
from datetime import timedelta

from apps.venues.models import Venue, VenueStatistic, VenueOperatingHour
from apps.events.models import Event, EventTicketTier, TicketPurchase, EventRSVP

User = get_user_model()

class DiscoveryAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='test@test.com', username='testuser', password='password123')
        self.client.force_authenticate(user=self.user)
        
        # Create venue
        self.venue = Venue.objects.create(
            owner=self.user,
            name='Test Venue',
            description='Test Description',
            address='123 Test St',
            location=Point(-122.4194, 37.7749, srid=4326), # SF coords
            is_active=True
        )
        
        VenueStatistic.objects.create(
            venue=self.venue,
            followers_count=100,
            average_rating=4.5
        )

        now = timezone.now()
        # Create event for tonight
        self.event = Event.objects.create(
            venue=self.venue,
            title='Test Event',
            description='Test Event Description',
            start_time=now + timedelta(hours=1),
            is_active=True
        )
        
        # Add some RSVPs to give it a score
        EventRSVP.objects.create(event=self.event, user=self.user, status='going')

    def test_global_search(self):
        url = reverse('discovery:search')
        response = self.client.get(url, {'q': 'Test', 'type': 'clubs'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('venues', data)
        self.assertEqual(len(data['venues']), 1)
        self.assertEqual(data['venues'][0]['name'], 'Test Venue')
        # Check annotated field
        self.assertEqual(data['venues'][0]['followers_count'], 100)

    def test_trending(self):
        url = reverse('discovery:trending')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('venues', data)
        self.assertIn('events', data)

    def test_trending_summary(self):
        url = reverse('discovery:trending_summary')
        response = self.client.get(url, {'lat': '37.7749', 'lng': '-122.4194'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['total_events_tonight'], 1)
        self.assertEqual(data['total_active_people'], 1)

    def test_heatmap_zones(self):
        url = reverse('discovery:heatmap_zones')
        response = self.client.get(url, {'lat': '37.7749', 'lng': '-122.4194'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('zones', data)
        self.assertEqual(len(data['zones']), 1)
        # Verify normalization
        self.assertEqual(data['zones'][0]['heat_percentage'], 100.0)
        self.assertEqual(data['zones'][0]['heat_level'], 'Insane')

    def test_heatmap_stats(self):
        url = reverse('discovery:heatmap_stats')
        response = self.client.get(url, {'lat': '37.7749', 'lng': '-122.4194'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['active_now'], 1)

    def test_nearby(self):
        url = reverse('discovery:nearby')
        response = self.client.get(url, {'lat': '37.7749', 'lng': '-122.4194'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('venues', data)
        self.assertEqual(len(data['venues']), 1)
        self.assertIn('distance', data['venues'][0])

