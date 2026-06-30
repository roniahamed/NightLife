from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Post, Comment, Like
from apps.venues.models import Venue
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

class SocialTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='password123')
        self.venue_user = User.objects.create_user(username='venueuser', email='venue@example.com', password='password123', registration_type='venue')
        self.venue = Venue.objects.create(owner=self.venue_user, name='Test Venue', address='123 Test St')
        
        # Authenticate
        self.client.force_authenticate(user=self.user)

    def test_create_post(self):
        response = self.client.post('/api/social/posts/', {
            'caption': 'Test post caption',
            'visibility': 'public',
            'tags': ['test', 'django']
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(Post.objects.first().caption, 'Test post caption')
        self.assertEqual(Post.objects.first().visibility, 'public')
        self.assertEqual(Post.objects.first().tags, ['test', 'django'])

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
        
    def test_create_story(self):
        # Create a dummy image file
        image_content = b'dummy_image_data'
        media_file = SimpleUploadedFile("test_story.jpg", image_content, content_type="image/jpeg")
        
        response = self.client.post('/api/social/stories/', {
            'media': media_file
        }, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
