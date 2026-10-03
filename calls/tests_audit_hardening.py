from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta, date, time
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import User
from campaigns.models import Campaign, Questionnaire, Question
from customers.models import Customer, CampaignCustomer
from calls.models import CallRecord, FollowUp, QuestionResponse
from analytics.models import Notification
from analytics.engine import compute_telecaller_performance, parse_date_range


class AuditHardeningTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin_auditor',
            email='admin@auditor.test',
            password='password123',
            role='ADMIN'
        )
        self.tc1 = User.objects.create_user(
            username='tc_one',
            email='tc1@auditor.test',
            password='password123',
            role='TELE_CALLER'
        )
        self.tc2 = User.objects.create_user(
            username='tc_two',
            email='tc2@auditor.test',
            password='password123',
            role='TELE_CALLER'
        )
        self.campaign = Campaign.objects.create(
            name='Test Hardening Campaign',
            description='Audit testing',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
            status='Active',
            target_calls=100,
            created_by=self.admin_user
        )
        self.customer = Customer.objects.create(
            name='Hardening Customer',
            phone='+15559998888',
            email='cust@auditor.test'
        )
        self.assignment = CampaignCustomer.objects.create(
            campaign=self.campaign,
            customer=self.customer,
            assigned_telecaller=self.tc1,
            assignment_status='Assigned'
        )

    # 1. Follow-up state transition tests
    def test_cannot_complete_already_completed_followup(self):
        """Completed follow-up cannot be completed again."""
        fu = FollowUp.objects.create(
            customer=self.customer,
            assigned_to=self.tc1,
            scheduled_date=timezone.now().date(),
            scheduled_time=time(14, 0),
            status='Completed'
        )
        self.client.login(username='tc_one', password='password123')
        response = self.client.post(reverse('followup_complete', kwargs={'pk': fu.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        fu.refresh_from_db()
        self.assertEqual(fu.status, 'Completed')
        messages_text = [m.message for m in response.context['messages']]
        self.assertTrue(any('cannot be marked complete' in m for m in messages_text))

    def test_cannot_cancel_already_completed_followup(self):
        """Completed follow-up cannot be cancelled."""
        fu = FollowUp.objects.create(
            customer=self.customer,
            assigned_to=self.tc1,
            scheduled_date=timezone.now().date(),
            scheduled_time=time(14, 0),
            status='Completed'
        )
        self.client.login(username='tc_one', password='password123')
        response = self.client.post(reverse('followup_cancel', kwargs={'pk': fu.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        fu.refresh_from_db()
        self.assertEqual(fu.status, 'Completed')

    def test_followup_reschedule_success(self):
        """Pending or Overdue follow-up can be rescheduled with valid date and time."""
        fu = FollowUp.objects.create(
            customer=self.customer,
            assigned_to=self.tc1,
            scheduled_date=timezone.now().date() - timedelta(days=2),
            scheduled_time=time(10, 0),
            status='Overdue'
        )
        self.client.login(username='tc_one', password='password123')
        new_date = (timezone.now().date() + timedelta(days=3)).strftime('%Y-%m-%d')
        response = self.client.post(reverse('followup_reschedule', kwargs={'pk': fu.pk}), {
            'scheduled_date': new_date,
            'scheduled_time': '16:30',
            'notes': 'Customer requested later callback'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        fu.refresh_from_db()
        self.assertEqual(str(fu.scheduled_date), new_date)
        self.assertEqual(str(fu.scheduled_time)[:5], '16:30')
        self.assertEqual(fu.status, 'Pending')
        self.assertEqual(fu.notes, 'Customer requested later callback')

    def test_cannot_reschedule_completed_followup(self):
        """Completed follow-up cannot be rescheduled."""
        fu = FollowUp.objects.create(
            customer=self.customer,
            assigned_to=self.tc1,
            scheduled_date=timezone.now().date(),
            scheduled_time=time(10, 0),
            status='Completed'
        )
        self.client.login(username='tc_one', password='password123')
        new_date = (timezone.now().date() + timedelta(days=1)).strftime('%Y-%m-%d')
        response = self.client.post(reverse('followup_reschedule', kwargs={'pk': fu.pk}), {
            'scheduled_date': new_date,
            'scheduled_time': '11:00'
        }, follow=True)
        fu.refresh_from_db()
        self.assertEqual(fu.status, 'Completed')

    # 2. Call duration upper limit
    def test_record_call_duration_exceeds_limit(self):
        """Call duration exceeding 24 hours is rejected."""
        self.client.login(username='tc_one', password='password123')
        response = self.client.post(reverse('record_call', kwargs={'assignment_id': self.assignment.pk}), {
            'call_status': 'No Answer',
            'duration': '90000',  # > 86400
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CallRecord.objects.filter(customer=self.customer).count(), 0)
        messages_text = [m.message for m in response.context['messages']]
        self.assertTrue(any('cannot exceed 24 hours' in m for m in messages_text))

    # 3. Campaign edit negative target calls validation
    def test_campaign_edit_rejects_negative_target(self):
        """campaign_edit rejects target_calls < 0."""
        self.client.login(username='admin_auditor', password='password123')
        response = self.client.post(reverse('campaign_edit', kwargs={'pk': self.campaign.pk}), {
            'name': self.campaign.name,
            'start_date': str(self.campaign.start_date),
            'end_date': str(self.campaign.end_date),
            'status': 'Active',
            'target_calls': '-10'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('Target calls cannot be negative.', response.content.decode())
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.target_calls, 100)

    # 4. Customer assign campaign status validation
    def test_customer_assign_rejects_completed_campaign(self):
        """customer_assign rejects assigning customers to a Completed campaign."""
        self.campaign.status = 'Completed'
        self.campaign.save()
        self.client.login(username='admin_auditor', password='password123')
        response = self.client.post(reverse('customer_assign'), {
            'campaign_id': self.campaign.pk,
            'telecaller_id': self.tc1.pk,
            'customer_ids': [self.customer.pk]
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        messages_text = [m.message for m in response.context['messages']]
        self.assertTrue(any('Only Draft or Active campaigns accept assignments' in m for m in messages_text))

    # 5. Report center telecaller filter consistency
    def test_compute_telecaller_performance_respects_filter(self):
        """compute_telecaller_performance filters by telecaller_id when supplied."""
        all_res = compute_telecaller_performance()
        self.assertGreaterEqual(len(all_res), 2)

        tc1_res = compute_telecaller_performance(telecaller_id=self.tc1.id)
        self.assertEqual(len(tc1_res), 1)
        self.assertEqual(tc1_res[0]['telecaller'].id, self.tc1.id)

    # 6. Notification smart redirect handles deleted/unassigned objects
    def test_notification_smart_redirect_deleted_campaign(self):
        """Notification for a deleted campaign redirects cleanly without 404."""
        notif = Notification.objects.create(
            recipient=self.tc1,
            title='Campaign Notice',
            message='Check campaign',
            related_object_type='campaign',
            related_object_id=999999  # Non-existent
        )
        self.client.login(username='tc_one', password='password123')
        response = self.client.post(reverse('notification_read_single', kwargs={'pk': notif.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)
        messages_text = [m.message for m in response.context['messages']]
        self.assertTrue(any('is no longer available' in m for m in messages_text))

    # 7. Campaign detail enrolled customers role-awareness
    def test_admin_enrolled_customers_no_record_call(self):
        """Admin viewing campaign detail does NOT see record_call links in Enrolled Customers."""
        self.client.login(username='admin_auditor', password='password123')
        response = self.client.get(reverse('campaign_detail', kwargs={'pk': self.campaign.pk}) + '?tab=customers')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn(f"/calls/record/{self.assignment.pk}/", content)
        self.assertIn("View Customer", content)

    # 8. Customer detail role-awareness
    def test_admin_customer_detail_no_record_call(self):
        """Admin viewing customer detail does NOT see start call console link."""
        self.client.login(username='admin_auditor', password='password123')
        response = self.client.get(reverse('customer_detail', kwargs={'pk': self.customer.pk}))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn(f"/calls/record/{self.assignment.pk}/", content)

    # 9. Customer import rejects .xls
    def test_customer_import_rejects_xls(self):
        """Customer import explicitly rejects legacy .xls format."""
        self.client.login(username='admin_auditor', password='password123')
        fake_file = SimpleUploadedFile("leads.xls", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", content_type="application/vnd.ms-excel")
        response = self.client.post(reverse('customer_import'), {'upload_file': fake_file}, follow=True)
        self.assertEqual(response.status_code, 200)
        messages_text = [m.message for m in response.context['messages']]
        self.assertTrue(any('Legacy Excel (.xls) format is not supported' in m for m in messages_text))

    # 10. Questionnaire builder question type validation
    def test_questionnaire_builder_rejects_invalid_type(self):
        """Questionnaire builder rejects unsupported question types."""
        self.client.login(username='admin_auditor', password='password123')
        response = self.client.post(reverse('questionnaire_builder', kwargs={'campaign_id': self.campaign.pk}), {
            'title': 'Test Q',
            'q_id[]': [''],
            'q_text[]': ['What is your opinion?'],
            'q_type[]': ['invalid_matrix_type'],
            'q_options[]': [''],
            'q_required[]': ['1']
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        messages_text = [m.message for m in response.context['messages']]
        self.assertTrue(any('Invalid question type' in m for m in messages_text))

    # 11. Follow-up state UI action matrix tests
    def test_pending_followup_renders_action_dropdown(self):
        """Pending follow-up renders action dropdown with Mark Complete, Reschedule, and Cancel."""
        fu = FollowUp.objects.create(
            customer=self.customer,
            assigned_to=self.tc1,
            scheduled_date=timezone.now().date() + timedelta(days=2),
            scheduled_time=time(11, 0),
            status='Pending'
        )
        self.client.login(username='tc_one', password='password123')
        response = self.client.get(reverse('followup_list'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(f'id="action-btn-{fu.pk}"', content)
        self.assertIn('Mark Complete', content)
        self.assertIn('Reschedule', content)
        self.assertIn('Cancel', content)

    def test_overdue_followup_renders_action_dropdown(self):
        """Overdue follow-up renders action dropdown with Mark Complete, Reschedule, and Cancel."""
        fu = FollowUp.objects.create(
            customer=self.customer,
            assigned_to=self.tc1,
            scheduled_date=timezone.now().date() - timedelta(days=1),
            scheduled_time=time(9, 0),
            status='Overdue'
        )
        self.client.login(username='tc_one', password='password123')
        response = self.client.get(reverse('followup_list'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(f'id="action-btn-{fu.pk}"', content)
        self.assertIn('Overdue', content)
        self.assertIn('Mark Complete', content)

    def test_completed_followup_renders_no_action_dropdown(self):
        """Completed follow-up renders Completed badge and NO action dropdown."""
        fu = FollowUp.objects.create(
            customer=self.customer,
            assigned_to=self.tc1,
            scheduled_date=timezone.now().date() - timedelta(days=1),
            scheduled_time=time(10, 0),
            status='Completed'
        )
        self.client.login(username='tc_one', password='password123')
        response = self.client.get(reverse('followup_list') + '?status=Completed')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn(f'id="action-btn-{fu.pk}"', content)
        self.assertIn('badge-success', content)
        self.assertIn('Completed', content)

    def test_cancelled_followup_renders_no_action_dropdown(self):
        """Cancelled follow-up renders Cancelled badge and NO action dropdown."""
        fu = FollowUp.objects.create(
            customer=self.customer,
            assigned_to=self.tc1,
            scheduled_date=timezone.now().date() + timedelta(days=1),
            scheduled_time=time(12, 0),
            status='Cancelled'
        )
        self.client.login(username='tc_one', password='password123')
        response = self.client.get(reverse('followup_list') + '?status=Cancelled')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn(f'id="action-btn-{fu.pk}"', content)
        self.assertIn('badge-secondary', content)
        self.assertIn('Cancelled', content)

    # 12. Follow-up state transition integrity & backend execution
    def test_followup_cancel_success(self):
        """Pending follow-up can be cancelled via POST."""
        fu = FollowUp.objects.create(
            customer=self.customer,
            assigned_to=self.tc1,
            scheduled_date=timezone.now().date() + timedelta(days=2),
            scheduled_time=time(15, 0),
            status='Pending'
        )
        self.client.login(username='tc_one', password='password123')
        response = self.client.post(reverse('followup_cancel', kwargs={'pk': fu.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        fu.refresh_from_db()
        self.assertEqual(fu.status, 'Cancelled')

    def test_unauthorized_telecaller_cannot_modify_followup(self):
        """Tele-caller cannot complete, cancel, or reschedule another tele-caller's follow-up."""
        fu = FollowUp.objects.create(
            customer=self.customer,
            assigned_to=self.tc1,
            scheduled_date=timezone.now().date() + timedelta(days=2),
            scheduled_time=time(15, 0),
            status='Pending'
        )
        # Login as tc_two
        self.client.login(username='tc_two', password='password123')

        # Try to complete
        res_comp = self.client.post(reverse('followup_complete', kwargs={'pk': fu.pk}), follow=True)
        fu.refresh_from_db()
        self.assertEqual(fu.status, 'Pending')
        messages_comp = [m.message for m in res_comp.context['messages']]
        self.assertIn("Permission denied.", messages_comp)

        # Try to cancel
        res_canc = self.client.post(reverse('followup_cancel', kwargs={'pk': fu.pk}), follow=True)
        fu.refresh_from_db()
        self.assertEqual(fu.status, 'Pending')
        messages_canc = [m.message for m in res_canc.context['messages']]
        self.assertIn("Permission denied.", messages_canc)

        # Try to reschedule
        res_resched = self.client.post(reverse('followup_reschedule', kwargs={'pk': fu.pk}), {
            'scheduled_date': '2026-10-10',
            'scheduled_time': '10:00'
        }, follow=True)
        fu.refresh_from_db()
        self.assertEqual(fu.status, 'Pending')
        self.assertNotEqual(str(fu.scheduled_date), '2026-10-10')
        messages_resched = [m.message for m in res_resched.context['messages']]
        self.assertIn("Permission denied.", messages_resched)

    # 13. Duplicate follow-up prevention
    def test_record_call_prevents_duplicate_active_followup(self):
        """Recording a call when an active follow-up already exists at the same date and time updates it instead of creating a duplicate."""
        target_date = (timezone.now().date() + timedelta(days=5)).strftime('%Y-%m-%d')
        target_time = '14:30'

        # Existing active follow-up
        existing_fu = FollowUp.objects.create(
            customer=self.customer,
            assigned_to=self.tc1,
            scheduled_date=target_date,
            scheduled_time=target_time,
            status='Pending',
            notes='Initial callback note'
        )

        initial_count = FollowUp.objects.filter(customer=self.customer).count()
        self.assertEqual(initial_count, 1)

        self.client.login(username='tc_one', password='password123')
        response = self.client.post(reverse('record_call', kwargs={'assignment_id': self.assignment.pk}), {
            'call_status': 'Follow-up Required',
            'duration': '120',
            'comments': 'Second call made',
            'followup_date': target_date,
            'followup_time': target_time,
            'followup_notes': 'Updated pricing callback notes'
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        # Follow-up count should still be 1 (no duplicate created!)
        final_count = FollowUp.objects.filter(customer=self.customer).count()
        self.assertEqual(final_count, 1)

        existing_fu.refresh_from_db()
        self.assertEqual(existing_fu.notes, 'Updated pricing callback notes')
        self.assertEqual(existing_fu.status, 'Pending')
        self.assertIsNotNone(existing_fu.call_record)
        self.assertEqual(existing_fu.call_record.comments, 'Second call made')

