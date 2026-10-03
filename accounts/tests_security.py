"""
CCM Security, RBAC & Performance Regression Tests
==================================================
Comprehensive test suite covering:
1. telecaller_required decorator enforcement (admin blocked with 403, telecaller blocked from admin views with 403, telecaller allowed on own views)
2. Questionnaire preview object-level authorization
3. Notification state changes requiring POST with CSRF and user isolation
4. Campaign status server-side validation (create & edit)
5. Question response unique constraint (UniqueConstraint)
6. Call duration non-negative check constraint (CheckConstraint) & form validation
7. Follow-up overdue bulk processing and notification generation
8. N+1 query regression tests for telecaller_list, campaign_list, and customer_list
9. Cross-telecaller IDOR & data isolation tests
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.db import IntegrityError, connection
from django.test.utils import CaptureQueriesContext
from datetime import date, timedelta
from accounts.models import User
from campaigns.models import Campaign, Questionnaire, Question
from customers.models import Customer, CampaignCustomer
from calls.models import CallRecord, FollowUp, QuestionResponse
from analytics.models import Notification


class TelecallerRequiredDecoratorTests(TestCase):
    """Verify telecaller_required decorator actually enforces TELE_CALLER role."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='sec_admin', password='password123', role='ADMIN'
        )
        self.telecaller = User.objects.create_user(
            username='sec_tc', password='password123', role='TELE_CALLER'
        )
        self.campaign = Campaign.objects.create(
            name='Sec Campaign', start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            status='Active', created_by=self.admin
        )
        self.customer = Customer.objects.create(name='Sec Cust', phone='+15550999')
        self.assignment = CampaignCustomer.objects.create(
            campaign=self.campaign, customer=self.customer,
            assigned_telecaller=self.telecaller, assignment_status='Assigned'
        )

    def test_unauthenticated_blocked_from_telecaller_view(self):
        """Unauthenticated users redirect to login."""
        target_url = reverse('record_call', kwargs={'assignment_id': self.assignment.id})
        response = self.client.get(target_url)
        self.assertRedirects(response, reverse('login'))

    def test_admin_blocked_from_telecaller_only_view(self):
        """ADMIN accessing telecaller-only URL must receive HTTP 403."""
        self.client.login(username='sec_admin', password='password123')
        response = self.client.get(
            reverse('record_call', kwargs={'assignment_id': self.assignment.id})
        )
        self.assertEqual(response.status_code, 403)

    def test_telecaller_blocked_from_admin_only_view(self):
        """TELE_CALLER accessing admin-only URL must receive HTTP 403."""
        self.client.login(username='sec_tc', password='password123')
        response = self.client.get(reverse('campaign_create'))
        self.assertEqual(response.status_code, 403)

    def test_telecaller_allowed_on_own_permitted_view(self):
        """TELE_CALLER accessing own permitted view must be allowed (HTTP 200)."""
        self.client.login(username='sec_tc', password='password123')
        response = self.client.get(
            reverse('record_call', kwargs={'assignment_id': self.assignment.id})
        )
        self.assertEqual(response.status_code, 200)


class QuestionnairePreviewRBACTests(TestCase):
    """Telecaller cannot preview arbitrary campaign questionnaires."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='prev_admin', password='password123', role='ADMIN'
        )
        self.tc1 = User.objects.create_user(
            username='prev_tc1', password='password123', role='TELE_CALLER'
        )
        self.tc2 = User.objects.create_user(
            username='prev_tc2', password='password123', role='TELE_CALLER'
        )

        self.campaign1 = Campaign.objects.create(
            name='TC1 Campaign', start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            status='Active', created_by=self.admin
        )
        self.campaign2 = Campaign.objects.create(
            name='TC2 Campaign', start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            status='Active', created_by=self.admin
        )

        self.customer1 = Customer.objects.create(name='Cust1', phone='+15550101')
        self.customer2 = Customer.objects.create(name='Cust2', phone='+15550102')

        CampaignCustomer.objects.create(
            campaign=self.campaign1, customer=self.customer1,
            assigned_telecaller=self.tc1, assignment_status='Assigned'
        )
        CampaignCustomer.objects.create(
            campaign=self.campaign2, customer=self.customer2,
            assigned_telecaller=self.tc2, assignment_status='Assigned'
        )

        Questionnaire.objects.create(
            campaign=self.campaign1, title='Survey 1', created_by=self.admin
        )
        Questionnaire.objects.create(
            campaign=self.campaign2, title='Survey 2', created_by=self.admin
        )

    def test_unauthenticated_user_rejected_from_preview(self):
        """Unauthenticated user is redirected to login."""
        target_url = reverse('questionnaire_preview', kwargs={'campaign_id': self.campaign1.id})
        response = self.client.get(target_url)
        self.assertRedirects(response, f"{reverse('login')}?next={target_url}")

    def test_admin_can_preview_any_questionnaire(self):
        """Admin can preview any campaign's questionnaire."""
        self.client.login(username='prev_admin', password='password123')
        for campaign in [self.campaign1, self.campaign2]:
            response = self.client.get(
                reverse('questionnaire_preview', kwargs={'campaign_id': campaign.id})
            )
            self.assertEqual(response.status_code, 200)

    def test_telecaller_can_preview_own_campaign_questionnaire(self):
        """Telecaller can preview questionnaire for their assigned campaign."""
        self.client.login(username='prev_tc1', password='password123')
        response = self.client.get(
            reverse('questionnaire_preview', kwargs={'campaign_id': self.campaign1.id})
        )
        self.assertEqual(response.status_code, 200)

    def test_telecaller_cannot_preview_other_campaign_questionnaire(self):
        """Telecaller cannot preview questionnaire for unassigned campaign."""
        self.client.login(username='prev_tc1', password='password123')
        response = self.client.get(
            reverse('questionnaire_preview', kwargs={'campaign_id': self.campaign2.id})
        )
        self.assertRedirects(response, reverse('campaign_list'))


class NotificationSecurityTests(TestCase):
    """Verify notification state changes require POST and enforce ownership."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='notif_user', password='password123', role='TELE_CALLER'
        )
        self.other_user = User.objects.create_user(
            username='notif_other', password='password123', role='TELE_CALLER'
        )
        self.client.login(username='notif_user', password='password123')

        self.notification = Notification.objects.create(
            recipient=self.user,
            notification_type='general',
            title='Test Notification',
            message='Test message',
            is_read=False
        )

    def test_get_notification_read_all_does_not_mutate(self):
        """GET to read-all should NOT mark notifications as read."""
        response = self.client.get(reverse('notification_read_all'))
        self.assertRedirects(response, reverse('notification_list'))
        self.notification.refresh_from_db()
        self.assertFalse(self.notification.is_read)

    def test_post_notification_read_all_marks_read(self):
        """POST to read-all should mark all as read."""
        response = self.client.post(reverse('notification_read_all'))
        self.assertRedirects(response, reverse('notification_list'))
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)

    def test_get_notification_read_single_does_not_mark_read(self):
        """GET to read-single should redirect but NOT mark read."""
        response = self.client.get(
            reverse('notification_read_single', kwargs={'pk': self.notification.pk})
        )
        self.notification.refresh_from_db()
        self.assertFalse(self.notification.is_read)

    def test_post_notification_read_single_marks_read(self):
        """POST to read-single should mark as read."""
        response = self.client.post(
            reverse('notification_read_single', kwargs={'pk': self.notification.pk})
        )
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)

    def test_notification_ownership_enforced(self):
        """Users cannot access or mutate other users' notifications."""
        other_notif = Notification.objects.create(
            recipient=self.other_user,
            title='Other Notification',
            message='Not yours',
            is_read=False
        )
        # GET returns 404
        response_get = self.client.get(
            reverse('notification_read_single', kwargs={'pk': other_notif.pk})
        )
        self.assertEqual(response_get.status_code, 404)

        # POST returns 404
        response_post = self.client.post(
            reverse('notification_read_single', kwargs={'pk': other_notif.pk})
        )
        self.assertEqual(response_post.status_code, 404)
        other_notif.refresh_from_db()
        self.assertFalse(other_notif.is_read)


class CampaignStatusValidationTests(TestCase):
    """Verify server-side campaign status validation for both create and edit."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='camp_admin', password='password123', role='ADMIN'
        )
        self.client.login(username='camp_admin', password='password123')

    def test_invalid_status_rejected_on_create(self):
        """Campaign creation with invalid status must be rejected."""
        response = self.client.post(reverse('campaign_create'), {
            'name': 'Test Campaign',
            'start_date': str(date.today()),
            'end_date': str(date.today() + timedelta(days=7)),
            'status': 'INVALID_STATUS',
            'target_calls': '10',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Campaign.objects.count(), 0)

    def test_valid_status_accepted_on_create(self):
        """Campaign creation with valid status should succeed."""
        response = self.client.post(reverse('campaign_create'), {
            'name': 'Valid Campaign',
            'start_date': str(date.today()),
            'end_date': str(date.today() + timedelta(days=7)),
            'status': 'Active',
            'target_calls': '50',
        })
        self.assertEqual(Campaign.objects.count(), 1)

    def test_invalid_status_rejected_on_edit(self):
        """Editing campaign with invalid status must be rejected."""
        campaign = Campaign.objects.create(
            name='Edit Test Campaign', start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            status='Draft', created_by=self.admin
        )
        response = self.client.post(reverse('campaign_edit', kwargs={'pk': campaign.pk}), {
            'name': 'Edit Test Campaign',
            'start_date': str(date.today()),
            'end_date': str(date.today() + timedelta(days=7)),
            'status': 'INJECTED_STATUS',
            'target_calls': '10',
        })
        self.assertEqual(response.status_code, 200)
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, 'Draft')

    def test_valid_status_accepted_on_edit(self):
        """Editing campaign with valid status must succeed."""
        campaign = Campaign.objects.create(
            name='Edit Valid Campaign', start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            status='Draft', created_by=self.admin
        )
        response = self.client.post(reverse('campaign_edit', kwargs={'pk': campaign.pk}), {
            'name': 'Edit Valid Campaign Updated',
            'start_date': str(date.today()),
            'end_date': str(date.today() + timedelta(days=7)),
            'status': 'Active',
            'target_calls': '20',
        })
        self.assertRedirects(response, reverse('campaign_detail', kwargs={'pk': campaign.pk}))
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, 'Active')


class CallDurationAndIntegrityTests(TestCase):
    """Test CallRecord CheckConstraint and application-level validation."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='cd_admin', password='password123', role='ADMIN'
        )
        self.tc = User.objects.create_user(
            username='cd_tc', password='password123', role='TELE_CALLER'
        )
        self.campaign = Campaign.objects.create(
            name='CD Campaign', start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            status='Active', created_by=self.admin
        )
        self.customer = Customer.objects.create(name='CD Customer', phone='+15550600')
        self.assignment = CampaignCustomer.objects.create(
            campaign=self.campaign, customer=self.customer,
            assigned_telecaller=self.tc, assignment_status='Assigned'
        )

    def test_negative_duration_rejected_by_db_check_constraint(self):
        """CheckConstraint call_duration_non_negative prevents negative duration in DB."""
        with self.assertRaises(IntegrityError):
            CallRecord.objects.create(
                campaign=self.campaign, customer=self.customer,
                telecaller=self.tc, call_status='Completed',
                call_start_time=timezone.now(), duration=-10
            )

    def test_negative_duration_rejected_in_form(self):
        """Application level validation in record_call rejects negative duration."""
        self.client.login(username='cd_tc', password='password123')
        response = self.client.post(
            reverse('record_call', kwargs={'assignment_id': self.assignment.id}),
            {'call_status': 'Completed', 'duration': '-25', 'comments': ''}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CallRecord.objects.count(), 0)

    def test_invalid_call_status_rejected_in_form(self):
        """Crafted POST with invalid call_status is rejected."""
        self.client.login(username='cd_tc', password='password123')
        response = self.client.post(
            reverse('record_call', kwargs={'assignment_id': self.assignment.id}),
            {'call_status': 'MALICIOUS_STATUS', 'duration': '30', 'comments': ''}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CallRecord.objects.count(), 0)

    def test_valid_call_record_created(self):
        """Valid call parameters successfully create CallRecord."""
        self.client.login(username='cd_tc', password='password123')
        response = self.client.post(
            reverse('record_call', kwargs={'assignment_id': self.assignment.id}),
            {'call_status': 'Completed', 'duration': '45', 'comments': 'Went well'}
        )
        self.assertEqual(CallRecord.objects.count(), 1)
        call = CallRecord.objects.first()
        self.assertEqual(call.duration, 45)
        self.assertEqual(call.call_status, 'Completed')


class QuestionResponseIntegrityTests(TestCase):
    """Test QuestionResponse UniqueConstraint(call_record, question)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='qr_admin', password='password123', role='ADMIN'
        )
        self.tc = User.objects.create_user(
            username='qr_tc', password='password123', role='TELE_CALLER'
        )
        self.campaign = Campaign.objects.create(
            name='QR Campaign', start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            status='Active', created_by=self.admin
        )
        self.customer = Customer.objects.create(name='QR Customer', phone='+15550700')
        self.call = CallRecord.objects.create(
            campaign=self.campaign, customer=self.customer,
            telecaller=self.tc, call_status='Completed',
            call_start_time=timezone.now(), duration=60
        )
        self.questionnaire = Questionnaire.objects.create(
            campaign=self.campaign, title='QR Survey', created_by=self.admin
        )
        self.question = Question.objects.create(
            questionnaire=self.questionnaire,
            question_text='How would you rate our service?',
            question_type='rating_scale'
        )

    def test_duplicate_response_prevented_by_unique_constraint(self):
        """Same question cannot receive multiple responses for the same call record."""
        QuestionResponse.objects.create(
            call_record=self.call, question=self.question, rating=5
        )
        with self.assertRaises(IntegrityError):
            QuestionResponse.objects.create(
                call_record=self.call, question=self.question, rating=4
            )


class FollowUpOverdueProcessingTests(TestCase):
    """Test follow-up overdue processing correctness."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='fu_admin', password='password123', role='ADMIN'
        )
        self.tc = User.objects.create_user(
            username='fu_tc', password='password123', role='TELE_CALLER'
        )
        self.customer = Customer.objects.create(name='FU Customer', phone='+15550800')

    def test_past_date_followup_marked_overdue(self):
        """Follow-up with past scheduled_date is marked Overdue and notification is created."""
        from calls.views import update_overdue_followups
        fu = FollowUp.objects.create(
            customer=self.customer, assigned_to=self.tc,
            scheduled_date=date.today() - timedelta(days=2),
            scheduled_time='10:00:00', status='Pending'
        )
        update_overdue_followups()
        fu.refresh_from_db()
        self.assertEqual(fu.status, 'Overdue')

        notifs = Notification.objects.filter(
            recipient=self.tc,
            related_object_type='followup',
            related_object_id=fu.id
        )
        self.assertTrue(notifs.exists())

    def test_future_date_followup_remains_pending(self):
        """Follow-up with future scheduled_date must remain Pending."""
        from calls.views import update_overdue_followups
        fu = FollowUp.objects.create(
            customer=self.customer, assigned_to=self.tc,
            scheduled_date=date.today() + timedelta(days=3),
            scheduled_time='10:00:00', status='Pending'
        )
        update_overdue_followups()
        fu.refresh_from_db()
        self.assertEqual(fu.status, 'Pending')


class CrossTelecallerIDORTests(TestCase):
    """Verify telecaller A cannot access telecaller B's data."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='idor_admin', password='password123', role='ADMIN'
        )
        self.tc_a = User.objects.create_user(
            username='idor_tc_a', password='password123', role='TELE_CALLER'
        )
        self.tc_b = User.objects.create_user(
            username='idor_tc_b', password='password123', role='TELE_CALLER'
        )

        self.campaign = Campaign.objects.create(
            name='IDOR Test Campaign',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            status='Active', created_by=self.admin
        )

        self.cust_a = Customer.objects.create(name='Customer A', phone='+15550301')
        self.cust_b = Customer.objects.create(name='Customer B', phone='+15550302')

        self.assign_a = CampaignCustomer.objects.create(
            campaign=self.campaign, customer=self.cust_a,
            assigned_telecaller=self.tc_a, assignment_status='Assigned'
        )
        self.assign_b = CampaignCustomer.objects.create(
            campaign=self.campaign, customer=self.cust_b,
            assigned_telecaller=self.tc_b, assignment_status='Assigned'
        )

        now = timezone.now()
        self.call_b = CallRecord.objects.create(
            campaign=self.campaign, customer=self.cust_b,
            telecaller=self.tc_b, call_status='Completed',
            call_start_time=now, duration=30
        )

        self.fu_b = FollowUp.objects.create(
            customer=self.cust_b, assigned_to=self.tc_b,
            scheduled_date=date.today() + timedelta(days=1),
            scheduled_time='10:00:00', status='Pending'
        )

    def test_telecaller_cannot_access_other_customers(self):
        """TC A cannot view TC B's customer detail."""
        self.client.login(username='idor_tc_a', password='password123')
        response = self.client.get(
            reverse('customer_detail', kwargs={'pk': self.cust_b.pk})
        )
        self.assertRedirects(response, reverse('customer_list'))

    def test_telecaller_cannot_record_call_for_others_assignment(self):
        """TC A cannot record a call for TC B's assignment."""
        self.client.login(username='idor_tc_a', password='password123')
        response = self.client.get(
            reverse('record_call', kwargs={'assignment_id': self.assign_b.id})
        )
        self.assertRedirects(response, reverse('customer_list'))

    def test_telecaller_cannot_view_other_call_success(self):
        """TC A cannot view TC B's call success page."""
        self.client.login(username='idor_tc_a', password='password123')
        response = self.client.get(
            reverse('call_success', kwargs={'call_id': self.call_b.id})
        )
        self.assertRedirects(response, reverse('dashboard'))

    def test_telecaller_cannot_complete_other_followup(self):
        """TC A cannot mark TC B's followup as completed."""
        self.client.login(username='idor_tc_a', password='password123')
        response = self.client.post(
            reverse('followup_complete', kwargs={'pk': self.fu_b.id})
        )
        self.assertRedirects(response, reverse('followup_list'))
        self.fu_b.refresh_from_db()
        self.assertEqual(self.fu_b.status, 'Pending')

    def test_telecaller_cannot_cancel_other_followup(self):
        """TC A cannot cancel TC B's followup."""
        self.client.login(username='idor_tc_a', password='password123')
        response = self.client.post(
            reverse('followup_cancel', kwargs={'pk': self.fu_b.id})
        )
        self.assertRedirects(response, reverse('followup_list'))
        self.fu_b.refresh_from_db()
        self.assertEqual(self.fu_b.status, 'Pending')


class NPlusOneQueryAuditTests(TestCase):
    """Verify that list views execute a small, bounded number of queries regardless of item count."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='n1_admin', password='password123', role='ADMIN'
        )
        self.client = Client()
        self.client.login(username='n1_admin', password='password123')

        # Create 8 telecallers
        self.telecallers = [
            User.objects.create_user(
                username=f'tc_{i}', password='password123', role='TELE_CALLER'
            )
            for i in range(8)
        ]
        # Create 6 campaigns
        self.campaigns = [
            Campaign.objects.create(
                name=f'Campaign {i}', start_date=date.today(),
                end_date=date.today() + timedelta(days=7),
                status='Active', created_by=self.admin
            )
            for i in range(6)
        ]
        # Create 15 customers
        self.customers = [
            Customer.objects.create(name=f'Customer {i}', phone=f'+15550{i:04d}')
            for i in range(15)
        ]
        for i, cust in enumerate(self.customers):
            CampaignCustomer.objects.create(
                campaign=self.campaigns[i % len(self.campaigns)],
                customer=cust,
                assigned_telecaller=self.telecallers[i % len(self.telecallers)],
                assignment_status='Assigned'
            )

    def test_telecaller_list_query_count_bounded(self):
        """telecaller_list should execute <= 8 queries total (was 4N+1 = 33+ queries)."""
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse('telecaller_list'))
            self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(ctx), 8, f"Too many queries in telecaller_list: {len(ctx)}")

    def test_campaign_list_query_count_bounded(self):
        """campaign_list should execute <= 8 queries total (was 3N+1 = 19+ queries)."""
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse('campaign_list'))
            self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(ctx), 8, f"Too many queries in campaign_list: {len(ctx)}")

    def test_customer_list_query_count_bounded(self):
        """customer_list should execute <= 10 queries total for 15 rows (was 3N+2 = 47+ queries)."""
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse('customer_list'))
            self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(ctx), 10, f"Too many queries in customer_list: {len(ctx)}")
