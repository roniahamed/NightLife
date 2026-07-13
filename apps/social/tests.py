from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Post, Comment, Like, SavedPost
from apps.venues.models import Venue
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.events.models import Event
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class SocialTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='password123', registration_type='user')
        self.venue_user = User.objects.create_user(username='venueuser', email='venue@example.com', password='password123', registration_type='venue')
        self.venue = Venue.objects.create(owner=self.venue_user, name='Test Venue', address='123 Test St')
        self.event = Event.objects.create(
            venue=self.venue, 
            title='Test Event', 
            description='Test Desc', 
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(days=1)
        )
        
        # Authenticate as general user by default
        self.client.force_authenticate(user=self.user)

    def test_create_post_general_user_with_tags(self):
        response = self.client.post('/api/social/posts/', {
            'caption': 'Test post caption',
            'mood': '🔥',
            'visibility': 'public',
            'tags': ['test', 'django'],
            'event': self.event.id,
            'location_venue': self.venue.id
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(Post.objects.first().caption, 'Test post caption')
        self.assertEqual(Post.objects.first().mood, '🔥')
        self.assertEqual(Post.objects.first().visibility, 'public')
        self.assertEqual(Post.objects.first().tags, ['test', 'django'])

    def test_create_post_general_user_without_tags_fails(self):
        response = self.client.post('/api/social/posts/', {
            'caption': 'This should fail',
            'visibility': 'public'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Post.objects.count(), 0)
        self.assertIn("General users must tag both an event and a venue to create a post.", str(response.data))

    def test_create_post_venue_user_without_tags_succeeds(self):
        self.client.force_authenticate(user=self.venue_user)
        response = self.client.post('/api/social/posts/', {
            'caption': 'Venue post',
            'mood': '🎉'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(Post.objects.first().caption, 'Venue post')
        self.assertEqual(Post.objects.first().mood, '🎉')

    def test_like_post(self):
        post = Post.objects.create(author=self.user, caption='Test post')
        response = self.client.post(f'/api/social/posts/{post.id}/like/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'liked')
        self.assertTrue(Like.objects.filter(post=post, user=self.user).exists())

        # Test unlike
        response = self.client.post(f'/api/social/posts/{post.id}/like/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'unliked')
        self.assertFalse(Like.objects.filter(post=post, user=self.user).exists())

    def test_add_comment(self):
        post = Post.objects.create(author=self.user, caption='Test post')
        response = self.client.post(f'/api/social/posts/{post.id}/comments/', {
            'text': 'Great post!'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(Comment.objects.first().text, 'Great post!')

    def test_save_post(self):
        post = Post.objects.create(author=self.user, caption='Test post')
        response = self.client.post(f'/api/social/posts/{post.id}/save_post/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'saved')
        self.assertTrue(SavedPost.objects.filter(post=post, user=self.user).exists())

        # Test unsave
        response = self.client.post(f'/api/social/posts/{post.id}/save_post/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'unsaved')
        self.assertFalse(SavedPost.objects.filter(post=post, user=self.user).exists())

    def test_share_post(self):
        post = Post.objects.create(author=self.user, caption='Test post')
        self.assertEqual(post.shares_count, 0)
        
        response = self.client.post(f'/api/social/posts/{post.id}/share/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'shared')
        self.assertEqual(response.data['shares_count'], 1)
        
        post.refresh_from_db()
        self.assertEqual(post.shares_count, 1)
        
    def test_create_story(self):
        # Create a dummy image file
        image_content = b'dummy_image_data'
        media_file = SimpleUploadedFile("test_story.jpg", image_content, content_type="image/jpeg")
        
        response = self.client.post('/api/social/stories/', {
            'media': media_file
        }, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
