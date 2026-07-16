from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from .models import Notification, FCMDevice

User = get_user_model()

class NotificationAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='notifuser',
            email='notifuser@example.com',
            password='testpassword123'
        )
        self.notification = Notification.objects.create(
            user=self.user,
            title='Test Notification',
            message='This is a test notification.'
        )

    def test_list_notifications(self):
        url = reverse('notification-list')
        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Test Notification')

    def test_list_notifications_unauthenticated(self):
        url = reverse('notification-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_mark_notification_read(self):
        url = reverse('notification-read', kwargs={'pk': self.notification.pk})
        self.client.force_authenticate(user=self.user)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)

    def test_mark_all_notifications_read(self):
        Notification.objects.create(
            user=self.user,
            title='Test 2',
            message='Second unread.'
        )
        url = reverse('notification-read-all')
        self.client.force_authenticate(user=self.user)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Notification.objects.filter(is_read=False).count(), 0)

    def test_register_fcm_device(self):
        url = reverse('fcm-device-register')
        self.client.force_authenticate(user=self.user)
        data = {
            'registration_id': 'fake-token-123',
            'device_type': 'android'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FCMDevice.objects.count(), 1)
        self.assertEqual(FCMDevice.objects.first().user, self.user)
