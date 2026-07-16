from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from .models import FAQ, LegalDocument, BugReport

User = get_user_model()

class SupportAPITests(APITestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com', 
            password='testpassword123',
            first_name='Test',
            last_name='User'
        )
        
        # Create test FAQ
        self.faq1 = FAQ.objects.create(question='What is this?', answer='This is a test FAQ.', order=1)
        self.faq2 = FAQ.objects.create(question='How do I use this?', answer='Just use it.', order=2)
        
        # Create test Legal Documents
        self.terms = LegalDocument.objects.create(document_type='terms', content='Terms of Service Content')
        self.privacy = LegalDocument.objects.create(document_type='privacy', content='Privacy Policy Content')

    def test_get_faqs(self):
        url = reverse('faqs')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        
        # Check if FAQs are returned and ordered correctly
        faqs = response.data['data']
        self.assertEqual(len(faqs), 2)
        self.assertEqual(faqs[0]['question'], self.faq1.question)
        self.assertEqual(faqs[1]['question'], self.faq2.question)

    def test_get_legal_document(self):
        url = reverse('legal-document', kwargs={'document_type': 'terms'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['data']['content'], self.terms.content)
        
        url_privacy = reverse('legal-document', kwargs={'document_type': 'privacy'})
        response_privacy = self.client.get(url_privacy)
        self.assertEqual(response_privacy.status_code, status.HTTP_200_OK)
        self.assertEqual(response_privacy.data['data']['content'], self.privacy.content)

    def test_get_nonexistent_legal_document(self):
        url = reverse('legal-document', kwargs={'document_type': 'guidelines'})
        response = self.client.get(url)
        # Should return standard 404 response
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_submit_bug_report_authenticated(self):
        url = reverse('report-bug')
        data = {
            'description': 'The app crashes when I click this button.',
            'steps_to_reproduce': '1. Open app 2. Click button 3. Crash'
        }
        
        # Authenticate
        self.client.force_authenticate(user=self.user)
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'success')
        
        # Verify it was saved to the database
        bug_reports = BugReport.objects.all()
        self.assertEqual(bug_reports.count(), 1)
        self.assertEqual(bug_reports[0].user, self.user)
        self.assertEqual(bug_reports[0].description, data['description'])

    def test_submit_bug_report_unauthenticated(self):
        url = reverse('report-bug')
        data = {
            'description': 'Anonymous bug report.',
        }
        
        # No authentication
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
