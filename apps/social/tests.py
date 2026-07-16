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
from PIL import Image
from io import BytesIO

def get_dummy_image():
    file = BytesIO()
    image = Image.new('RGB', size=(100, 100), color=(255, 0, 0))
    image.save(file, 'jpeg')
    file.name = 'test.jpg'
    file.seek(0)
    return file.read()

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
            'venue': self.venue.id
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(Post.objects.first().caption, 'Test post caption')
        self.assertEqual(Post.objects.first().mood, '🔥')
        self.assertEqual(Post.objects.first().visibility, 'public')
        self.assertEqual(Post.objects.first().tags, ['test', 'django'])

    def test_create_post_with_media_generates_thumbnail(self):
        media_file = SimpleUploadedFile("test_media.jpg", get_dummy_image(), content_type="image/jpeg")
        response = self.client.post('/api/social/posts/', {
            'caption': 'Post with media',
            'venue': self.venue.id,
            'media': [media_file]
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        post = Post.objects.first()
        self.assertEqual(post.media.count(), 1)
        media_obj = post.media.first()
        self.assertIsNotNone(media_obj.thumbnail)
        self.assertTrue(media_obj.thumbnail.name.startswith('social/thumbnails/'))

    def test_create_post_general_user_without_tags_fails(self):
        response = self.client.post('/api/social/posts/', {
            'caption': 'This should fail',
            'visibility': 'public'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Post.objects.count(), 0)
        self.assertIn("General users must tag either an event or a venue to create a post.", str(response.data))

    def test_create_post_general_user_only_venue_succeeds(self):
        response = self.client.post('/api/social/posts/', {
            'caption': 'Venue only post',
            'visibility': 'public',
            'venue': self.venue.id
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(Post.objects.first().caption, 'Venue only post')

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
        image_content = get_dummy_image()
        media_file = SimpleUploadedFile("test_story.jpg", image_content, content_type="image/jpeg")
        
        response = self.client.post('/api/social/stories/', {
            'media': media_file
        }, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_text_story(self):
        response = self.client.post('/api/social/stories/', {
            'text_content': 'Hello this is a text story!',
            'bg_color': '#FF5733'
        })
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['media_type'], 'text')
        self.assertEqual(response.data['text_content'], 'Hello this is a text story!')
        self.assertEqual(response.data['bg_color'], '#FF5733')

    def test_list_posts(self):
        Post.objects.create(author=self.user, caption='User post')
        Post.objects.create(author=self.venue_user, caption='Venue post', venue_profile=self.venue)
        
        response = self.client.get('/api/social/posts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

        # Test venue feed filter
        response = self.client.get('/api/social/posts/?venue_feed=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['caption'], 'Venue post')

    def test_list_comments(self):
        post = Post.objects.create(author=self.user, caption='Test post')
        Comment.objects.create(user=self.user, post=post, text='First comment')
        Comment.objects.create(user=self.venue_user, post=post, text='Second comment')
        
        response = self.client.get(f'/api/social/posts/{post.id}/comments/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_reply_to_comment(self):
        post = Post.objects.create(author=self.user, caption='Test post')
        parent_comment = Comment.objects.create(user=self.user, post=post, text='Parent comment')
        
        response = self.client.post(f'/api/social/posts/{post.id}/comments/', {
            'text': 'Reply comment',
            'parent': parent_comment.id
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.count(), 2)
        
        # Ensure the reply isn't fetched as a top-level comment
        response = self.client.get(f'/api/social/posts/{post.id}/comments/')
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['replies_count'], 1)

    def test_list_stories(self):
        from .models import Story
        Story.objects.create(author=self.user, expires_at=timezone.now() + timedelta(hours=24))
        Story.objects.create(author=self.user, expires_at=timezone.now() + timedelta(hours=24))
        # Expired story
        Story.objects.create(author=self.user, expires_at=timezone.now() - timedelta(hours=1))
        
        # Another user's story
        Story.objects.create(author=self.venue_user, expires_at=timezone.now() + timedelta(hours=24), venue_profile=self.venue)
        
        response = self.client.get('/api/social/stories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have 2 groups (testuser and venueuser)
        self.assertEqual(len(response.data), 2)
        # testuser group should have 2 stories
        user_group = next(g for g in response.data if g.get('user') is not None)
        self.assertEqual(len(user_group['stories']), 2)
        # venueuser group should have 1 story
        venue_group = next(g for g in response.data if g.get('venue') is not None)
        self.assertEqual(len(venue_group['stories']), 1)

    def test_retrieve_story(self):
        from .models import Story
        story = Story.objects.create(author=self.user, expires_at=timezone.now() + timedelta(hours=24))
        response = self.client.get(f'/api/social/stories/{story.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(story.id))

    def test_delete_story_by_owner(self):
        from .models import Story
        story = Story.objects.create(author=self.user, expires_at=timezone.now() + timedelta(hours=24))
        response = self.client.delete(f'/api/social/stories/{story.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Story.objects.count(), 0)

    def test_delete_story_by_other_user_fails(self):
        from .models import Story
        story = Story.objects.create(author=self.venue_user, expires_at=timezone.now() + timedelta(hours=24))
        response = self.client.delete(f'/api/social/stories/{story.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Story.objects.count(), 1)

    def test_report_post(self):
        post = Post.objects.create(author=self.venue_user, caption='Inappropriate post')
        response = self.client.post(f'/api/social/posts/{post.id}/report/', {
            'reason': 'spam',
            'description': 'This is spam'
        })
        print(response.content)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['reason'], 'spam')
        
        from .models import PostReport
        self.assertEqual(PostReport.objects.count(), 1)
        report = PostReport.objects.first()
        self.assertEqual(report.reporter, self.user)
        self.assertEqual(report.post, post)

    def test_report_comment(self):
        post = Post.objects.create(author=self.venue_user, caption='Nice post')
        comment = Comment.objects.create(user=self.venue_user, post=post, text='Inappropriate comment')
        
        response = self.client.post(f'/api/social/comments/{comment.id}/report/', {
            'reason': 'harassment',
            'description': 'This is harassment'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['reason'], 'harassment')
        
        from .models import CommentReport
        self.assertEqual(CommentReport.objects.count(), 1)
        report = CommentReport.objects.first()
        self.assertEqual(report.reporter, self.user)
        self.assertEqual(report.comment, comment)
