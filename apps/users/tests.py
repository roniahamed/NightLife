from rest_framework.test import APITestCase
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import UserFollow, UserBlock, UserReport

User = get_user_model()

class UserModuleTests(APITestCase):

    def setUp(self):
        # Create user 1
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='Password123!',
            first_name='User',
            last_name='One',
            is_active=True,
            is_email_verified=True
        )
        
        # Create user 2
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='Password123!',
            first_name='User',
            last_name='Two',
            is_active=True,
            is_email_verified=True
        )

        # Create user 3
        self.user3 = User.objects.create_user(
            username='user3',
            email='user3@example.com',
            password='Password123!',
            first_name='User',
            last_name='Three',
            is_active=True,
            is_email_verified=True
        )

    def test_profile_retrieve(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'user1@example.com')

    def test_profile_update(self):
        self.client.force_authenticate(user=self.user1)
        data = {'first_name': 'Updated', 'bio': 'New bio'}
        response = self.client.patch(reverse('profile'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.first_name, 'Updated')
        self.assertEqual(self.user1.bio, 'New bio')

    def test_public_profile(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(reverse('public-profile', kwargs={'username': self.user2.username}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['username'], 'user2')

    def test_follow_user(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(reverse('follow-user', kwargs={'username': self.user2.username}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(UserFollow.objects.filter(follower=self.user1, following=self.user2).exists())
        
        # Test Unfollow
        response = self.client.post(reverse('follow-user', kwargs={'username': self.user2.username}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(UserFollow.objects.filter(follower=self.user1, following=self.user2).exists())

    def test_followers_list(self):
        UserFollow.objects.create(follower=self.user1, following=self.user2)
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(reverse('followers-list', kwargs={'username': self.user2.username}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['follower_username'], 'user1')

    def test_following_list(self):
        UserFollow.objects.create(follower=self.user1, following=self.user2)
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(reverse('following-list', kwargs={'username': self.user1.username}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['following_username'], 'user2')

    def test_block_user(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(reverse('block-user', kwargs={'username': self.user2.username}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(UserBlock.objects.filter(blocker=self.user1, blocked=self.user2).exists())
        
        # After blocking, user1 shouldn't be able to follow user2
        follow_response = self.client.post(reverse('follow-user', kwargs={'username': self.user2.username}))
        self.assertEqual(follow_response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Test Unblock
        response = self.client.post(reverse('block-user', kwargs={'username': self.user2.username}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(UserBlock.objects.filter(blocker=self.user1, blocked=self.user2).exists())

    def test_blocked_users_list(self):
        UserBlock.objects.create(blocker=self.user1, blocked=self.user2)
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(reverse('blocked-users-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['blocked_username'], 'user2')

    def test_report_user(self):
        self.client.force_authenticate(user=self.user1)
        data = {'reason': 'Spam', 'description': 'Sending spam messages'}
        response = self.client.post(reverse('report-user', kwargs={'username': self.user2.username}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(UserReport.objects.filter(reporter=self.user1, reported_user=self.user2, reason='Spam').exists())

    def test_user_settings_retrieve(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(reverse('user-settings'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_activity_status_visible'])
        self.assertFalse(response.data['notify_sms'])

    def test_user_settings_update(self):
        self.client.force_authenticate(user=self.user1)
        data = {'is_activity_status_visible': False, 'notify_sms': True}
        response = self.client.patch(reverse('user-settings'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_activity_status_visible'])
        self.assertTrue(response.data['notify_sms'])
        
        self.user1.settings.refresh_from_db()
        self.assertFalse(self.user1.settings.is_activity_status_visible)
        self.assertTrue(self.user1.settings.notify_sms)
