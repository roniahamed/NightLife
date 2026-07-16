from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from .models import FAQ, TermsAndCondition, PrivacyPolicy, CommunityGuideline, BugReport

User = get_user_model()

class SupportAPITests(APITestCase):
    def setUp(self):
        # Create normal user
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com', 
            password='testpassword123',
            first_name='Test',
            last_name='User'
        )
        
        # Create admin user
        self.admin_user = User.objects.create_superuser(
            username='adminuser',
            email='adminuser@example.com', 
            password='adminpassword123',
        )
        
        # Create test FAQ
        self.faq1 = FAQ.objects.create(question='What is this?', answer='This is a test FAQ.', order=1)
        self.faq2 = FAQ.objects.create(question='How do I use this?', answer='Just use it.', order=2)
        
        # Create test Legal Documents
        self.terms = TermsAndCondition.objects.create(content='Terms of Service Content')
        self.privacy = PrivacyPolicy.objects.create(content='Privacy Policy Content')
        self.guideline = CommunityGuideline.objects.create(content='Community Guideline Content')

    def test_get_faqs(self):
        url = reverse('faqs')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        
        faqs = response.data['data']
        self.assertEqual(len(faqs), 2)

    def test_create_faq_admin(self):
        url = reverse('faqs')
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(url, {'question': 'New FAQ', 'answer': 'New Answer', 'order': 3})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FAQ.objects.count(), 3)

    def test_create_faq_unauthorized(self):
        url = reverse('faqs')
        # Normal user
        self.client.force_authenticate(user=self.user)
        response = self.client.post(url, {'question': 'New FAQ', 'answer': 'New Answer', 'order': 3})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Unauthenticated
        self.client.logout()
        response2 = self.client.post(url, {'question': 'New FAQ', 'answer': 'New Answer', 'order': 3})
        self.assertEqual(response2.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_terms(self):
        url = reverse('terms-detail', kwargs={'pk': self.terms.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['content'], self.terms.content)

    def test_patch_terms_admin(self):
        url = reverse('terms-detail', kwargs={'pk': self.terms.pk})
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.patch(url, {'content': 'Updated Terms'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.terms.refresh_from_db()
        self.assertEqual(self.terms.content, 'Updated Terms')

    def test_patch_terms_unauthorized(self):
        url = reverse('terms-detail', kwargs={'pk': self.terms.pk})
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(url, {'content': 'Updated Terms'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_get_privacy_policy(self):
        url = reverse('privacy-policy-detail', kwargs={'pk': self.privacy.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_community_guideline(self):
        url = reverse('community-guidelines-detail', kwargs={'pk': self.guideline.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['content'], self.guideline.content)

    def test_get_nonexistent_terms(self):
        url = reverse('terms-detail', kwargs={'pk': 9999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_submit_bug_report_authenticated(self):
        url = reverse('report-bug')
        data = {
            'description': 'The app crashes.',
        }
        self.client.force_authenticate(user=self.user)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BugReport.objects.count(), 1)
        
    def test_submit_bug_report_unauthenticated(self):
        url = reverse('report-bug')
        data = {'description': 'Anonymous bug report.'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

