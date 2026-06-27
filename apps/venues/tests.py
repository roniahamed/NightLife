from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from .models import Venue, Amenity, VenueOperatingHour, VenueReview, VenueGallery, VenueCategory, VenueFollow

User = get_user_model()

class VenueTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpassword123',
            username='testuser',
            registration_type='venue'
        )
        self.client.force_authenticate(user=self.user)
        
        self.amenity1 = Amenity.objects.create(name='Wi-Fi')
        self.amenity2 = Amenity.objects.create(name='Parking')
        self.category1 = VenueCategory.objects.create(name='EDM')
        
        self.venue_data = {
            'name': 'Test Venue',
            'description': 'A great place',
            'address': '123 Main St',
            'email': 'contact@testvenue.com',
            'amenity_ids': [self.amenity1.id, self.amenity2.id],
            'category_ids': [self.category1.id],
            'price_tier': 3,
            'capacity': 3000,
            'latitude': 37.7749,
            'longitude': -122.4194
        }

    def test_create_venue(self):
        url = reverse('venue-list')
        response = self.client.post(url, self.venue_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Venue.objects.count(), 1)
        venue = Venue.objects.first()
        self.assertEqual(venue.name, 'Test Venue')
        self.assertEqual(venue.owner, self.user)
        self.assertEqual(venue.amenities.count(), 2)
        self.assertEqual(venue.categories.count(), 1)
        self.assertEqual(venue.price_tier, 3)
        self.assertEqual(venue.capacity, 3000)
        self.assertIsNotNone(venue.statistic)
        self.assertEqual(venue.location.y, 37.7749)
        self.assertEqual(venue.location.x, -122.4194)

    def test_update_venue(self):
        venue = Venue.objects.create(
            owner=self.user,
            name='Old Name',
            description='Old Description',
            address='Old Address'
        )
        url = reverse('venue-detail', kwargs={'pk': venue.id})
        update_data = {
            'name': 'New Name',
            'description': 'New Description',
            'latitude': 40.7128,
            'longitude': -74.0060
        }
        response = self.client.patch(url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        venue.refresh_from_db()
        self.assertEqual(venue.name, 'New Name')
        self.assertEqual(venue.location.y, 40.7128)
        self.assertEqual(venue.location.x, -74.0060)

    def test_retrieve_venue_increments_views(self):
        venue = Venue.objects.create(owner=self.user, name='Retrieve Venue')
        # Stats creation happens in service on creation, but we bypassed it by direct model creation.
        # Let's ensure stats exist.
        from .models import VenueStatistic
        VenueStatistic.objects.create(venue=venue)
        
        url = reverse('venue-detail', kwargs={'pk': venue.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        venue.statistic.refresh_from_db()
        self.assertEqual(venue.statistic.total_views, 1)

    def test_follow_unfollow_venue(self):
        venue = Venue.objects.create(owner=self.user, name='Followable Venue')
        # Stats creation happens in service on creation, manually add
        from .models import VenueStatistic
        VenueStatistic.objects.create(venue=venue)
        
        user2 = User.objects.create_user(email='u2@example.com', password='pw', username='u2')
        self.client.force_authenticate(user=user2)
        
        follow_url = reverse('venue-follow', kwargs={'pk': venue.id})
        unfollow_url = reverse('venue-unfollow', kwargs={'pk': venue.id})
        
        # Follow
        response = self.client.post(follow_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(VenueFollow.objects.filter(user=user2, venue=venue).exists())
        
        venue.statistic.refresh_from_db()
        self.assertEqual(venue.statistic.followers_count, 1)
        
        # Unfollow
        response = self.client.post(unfollow_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(VenueFollow.objects.filter(user=user2, venue=venue).exists())
        
        venue.statistic.refresh_from_db()
        self.assertEqual(venue.statistic.followers_count, 0)

class VenueOperatingHourTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password='pw', username='u')
        self.client.force_authenticate(user=self.user)
        self.venue = Venue.objects.create(owner=self.user, name='Venue 1', description='Desc', address='Addr')

    def test_bulk_update_hours(self):
        url = reverse('venue-hours-bulk', kwargs={'venue_pk': self.venue.id})
        data = [
            {'day_of_week': 0, 'open_time': '09:00:00', 'close_time': '17:00:00', 'is_closed': False},
            {'day_of_week': 1, 'is_closed': True},
        ]
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.venue.operating_hours.count(), 2)
        monday_hours = self.venue.operating_hours.get(day_of_week=0)
        self.assertEqual(str(monday_hours.open_time), '09:00:00')

class VenueReviewTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(email='user1@example.com', password='pw', username='u1')
        self.user2 = User.objects.create_user(email='user2@example.com', password='pw', username='u2')
        self.venue = Venue.objects.create(owner=self.user1, name='Venue 1', description='Desc', address='Addr')
        
    def test_create_review_updates_stats(self):
        self.client.force_authenticate(user=self.user2)
        url = reverse('venue-reviews-list', kwargs={'venue_pk': self.venue.id})
        data = {'rating': 4, 'comment': 'Good place'}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        self.venue.statistic.refresh_from_db()
        self.assertEqual(self.venue.statistic.total_reviews, 1)
        self.assertEqual(self.venue.statistic.average_rating, 4.00)
        
        # Second review
        self.client.force_authenticate(user=self.user1)
        response2 = self.client.post(url, {'rating': 2, 'comment': 'Bad place'}, format='json')
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        
        self.venue.statistic.refresh_from_db()
        self.assertEqual(self.venue.statistic.total_reviews, 2)
        self.assertEqual(self.venue.statistic.average_rating, 3.00) # (4+2)/2

class VenueCategoryTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password='pw', username='u')
        self.client.force_authenticate(user=self.user)
        self.url = reverse('venue-categories-list')

    def test_create_category(self):
        response = self.client.post(self.url, {'name': 'Lounge'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(VenueCategory.objects.count(), 1)
        self.assertEqual(VenueCategory.objects.first().name, 'Lounge')

    def test_list_categories(self):
        VenueCategory.objects.create(name='Bar')
        VenueCategory.objects.create(name='Club')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
