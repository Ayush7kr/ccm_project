from django.test import TestCase, Client
from django.urls import reverse
from datetime import date, timedelta
from accounts.models import User
from campaigns.models import Campaign, Questionnaire, Question

class CampaignTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username='admin_c', password='password123', role='ADMIN')
        self.client.login(username='admin_c', password='password123')

    def test_campaign_creation(self):
        response = self.client.post(reverse('campaign_create'), {
            'name': 'New Test Campaign',
            'description': 'Testing campaign creation',
            'campaign_type': 'Tele-calling',
            'start_date': str(date.today()),
            'end_date': str(date.today() + timedelta(days=10)),
            'status': 'Active',
            'target_calls': '100'
        })
        self.assertEqual(Campaign.objects.filter(name='New Test Campaign').count(), 1)

    def test_questionnaire_creation(self):
        campaign = Campaign.objects.create(
            name='Q Test Campaign',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            created_by=self.admin
        )
        response = self.client.post(reverse('questionnaire_builder', kwargs={'campaign_id': campaign.id}), {
            'title': 'Test Survey',
            'description': 'Test instructions',
            'q_id[]': [''],
            'q_text[]': ['How satisfied are you?'],
            'q_type[]': ['rating_scale'],
            'q_options[]': [''],
            'q_required[]': ['1']
        })
        q = Questionnaire.objects.get(campaign=campaign)
        self.assertEqual(q.questions.count(), 1)

    def test_campaign_status_lifecycle(self):
        campaign = Campaign.objects.create(
            name='Lifecycle Campaign',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            status='Draft',
            created_by=self.admin
        )

        # Draft -> Completed should be rejected
        res = self.client.post(reverse('campaign_status_toggle', kwargs={'pk': campaign.id}), {'status': 'Completed'})
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, 'Draft')

        # Draft -> Active should succeed
        res = self.client.post(reverse('campaign_status_toggle', kwargs={'pk': campaign.id}), {'status': 'Active'})
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, 'Active')

        # Active -> Paused should succeed
        res = self.client.post(reverse('campaign_status_toggle', kwargs={'pk': campaign.id}), {'status': 'Paused'})
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, 'Paused')

        # Paused -> Active should succeed
        res = self.client.post(reverse('campaign_status_toggle', kwargs={'pk': campaign.id}), {'status': 'Active'})
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, 'Active')

        # Active -> Completed should succeed
        res = self.client.post(reverse('campaign_status_toggle', kwargs={'pk': campaign.id}), {'status': 'Completed'})
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, 'Completed')

    def test_campaign_detail_analytics_tab(self):
        campaign = Campaign.objects.create(
            name='Analytics Tab Campaign',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            status='Active',
            created_by=self.admin
        )
        response = self.client.get(reverse('campaign_detail', kwargs={'pk': campaign.id}) + '?tab=analytics')
        self.assertEqual(response.status_code, 200)
        self.assertIn('question_analytics', response.context)
        self.assertIn('status_counts', response.context)

