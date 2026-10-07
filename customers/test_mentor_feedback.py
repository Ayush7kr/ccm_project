from django.test import TestCase
from django.urls import reverse
from django.db import IntegrityError
from django.utils import timezone

from accounts.models import User
from campaigns.models import Campaign, Questionnaire, Question
from customers.models import Customer, CampaignCustomer
from calls.models import CallRecord, QuestionResponse, FollowUp
from analytics.models import Notification


class MentorFeedbackAssignmentTests(TestCase):
    """
    Mentor Feedback Regression Tests: Assignment & Shifting
    Tests 1 to 10
    """
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin_mentor',
            email='admin_mentor@test.com',
            password='Password123!',
            role='ADMIN'
        )
        self.tc1 = User.objects.create_user(
            username='tc_agent1',
            email='tc1@test.com',
            password='Password123!',
            role='TELE_CALLER',
            is_active=True
        )
        self.tc2 = User.objects.create_user(
            username='tc_agent2',
            email='tc2@test.com',
            password='Password123!',
            role='TELE_CALLER',
            is_active=True
        )
        self.inactive_tc = User.objects.create_user(
            username='tc_inactive',
            email='tc_inactive@test.com',
            password='Password123!',
            role='TELE_CALLER',
            is_active=False
        )
        self.non_tc = User.objects.create_user(
            username='manager_user',
            email='manager@test.com',
            password='Password123!',
            role='ADMIN',
            is_active=True
        )
        self.campaign = Campaign.objects.create(
            name='Q4 High Priority Campaign',
            status='Active',
            start_date=timezone.now().date(),
            end_date=(timezone.now() + timezone.timedelta(days=30)).date(),
            created_by=self.admin
        )

        # Setup exactly: 20 total customers, 16 assigned to TC1, 4 unassigned
        self.assigned_customers = []
        for i in range(16):
            cust = Customer.objects.create(name=f'Assigned Customer {i+1}', phone=f'+155500010{i:02d}', is_active=True)
            CampaignCustomer.objects.create(
                campaign=self.campaign,
                customer=cust,
                assigned_telecaller=self.tc1,
                assignment_status='Assigned'
            )
            self.assigned_customers.append(cust)

        self.unassigned_customers = []
        for i in range(4):
            cust = Customer.objects.create(name=f'Unassigned Customer {i+1}', phone=f'+155500020{i:02d}', is_active=True)
            CampaignCustomer.objects.create(
                campaign=self.campaign,
                customer=cust,
                assigned_telecaller=None,
                assignment_status='Unassigned'
            )
            self.unassigned_customers.append(cust)

        self.client.force_login(self.admin)

    def test_01_total_customer_count_is_correct(self):
        """1. Total customer count is correct (20 total customers)."""
        response = self.client.get(f"{reverse('customer_assign')}?campaign_id={self.campaign.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_count'], 20)
        self.assertContains(response, '20')

    def test_02_assigned_count_is_correct(self):
        """2. Assigned count is correct (16 assigned)."""
        response = self.client.get(f"{reverse('customer_assign')}?campaign_id={self.campaign.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['assigned_count'], 16)
        self.assertContains(response, '16')

    def test_03_remaining_count_is_correct(self):
        """3. Remaining count is correct (4 remaining)."""
        response = self.client.get(f"{reverse('customer_assign')}?campaign_id={self.campaign.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['unassigned_count'], 4)
        self.assertContains(response, '4')

    def test_04_only_unassigned_active_customers_are_selectable(self):
        """4. Only unassigned active customers are selectable in the new assignment list."""
        # Also create an inactive unassigned customer
        inactive_cust = Customer.objects.create(name='Inactive Lead', phone='+15550009999', is_active=False)
        CampaignCustomer.objects.create(campaign=self.campaign, customer=inactive_cust, assigned_telecaller=None)

        response = self.client.get(f"{reverse('customer_assign')}?campaign_id={self.campaign.id}")
        selectable = list(response.context['customers'])

        # Exactly 4 unassigned active customers should be in the selectable list
        self.assertEqual(len(selectable), 4)
        for cust in self.unassigned_customers:
            self.assertIn(cust, selectable)

        # None of the 16 assigned customers should be selectable
        for cust in self.assigned_customers:
            self.assertNotIn(cust, selectable)

        # Inactive customer must NOT be selectable
        self.assertNotIn(inactive_cust, selectable)

    def test_05_already_assigned_customer_cannot_be_newly_assigned(self):
        """5. Backend rejects attempts to newly assign already-assigned customers."""
        already_assigned = self.assigned_customers[0]
        link_before = CampaignCustomer.objects.get(campaign=self.campaign, customer=already_assigned)
        self.assertEqual(link_before.assigned_telecaller, self.tc1)

        # Crafted POST attempting to reassign via normal assignment
        response = self.client.post(reverse('customer_assign'), {
            'campaign_id': self.campaign.id,
            'telecaller_id': self.tc2.id,
            'customer_ids': [already_assigned.id]
        })

        # Verification: assignment was rejected and telecaller remains tc1
        link_after = CampaignCustomer.objects.get(campaign=self.campaign, customer=already_assigned)
        self.assertEqual(link_after.assigned_telecaller, self.tc1)

    def test_06_admin_can_shift_customer_between_telecallers(self):
        """6. Admin can shift an already-assigned customer to another tele-caller."""
        customer_to_shift = self.assigned_customers[0]
        link = CampaignCustomer.objects.get(campaign=self.campaign, customer=customer_to_shift)
        self.assertEqual(link.assigned_telecaller, self.tc1)

        response = self.client.post(reverse('customer_shift'), {
            'campaign_id': self.campaign.id,
            'destination_telecaller_id': self.tc2.id,
            'customer_ids': [customer_to_shift.id]
        })

        link.refresh_from_db()
        self.assertEqual(link.assigned_telecaller, self.tc2)

        # Destination telecaller receives notification
        notif = Notification.objects.filter(recipient=self.tc2, notification_type='assignment').first()
        self.assertIsNotNone(notif)
        self.assertIn(self.campaign.name, notif.message)

    def test_07_telecaller_cannot_shift_customers(self):
        """7. Tele-caller cannot shift customers (403 Forbidden)."""
        self.client.force_login(self.tc1)
        customer_to_shift = self.assigned_customers[0]

        response = self.client.post(reverse('customer_shift'), {
            'campaign_id': self.campaign.id,
            'destination_telecaller_id': self.tc2.id,
            'customer_ids': [customer_to_shift.id]
        })

        self.assertEqual(response.status_code, 403)
        link = CampaignCustomer.objects.get(campaign=self.campaign, customer=customer_to_shift)
        self.assertEqual(link.assigned_telecaller, self.tc1)

    def test_08_inactive_telecaller_cannot_receive_shifted_customers(self):
        """8. Inactive tele-caller cannot receive shifted customers."""
        customer_to_shift = self.assigned_customers[0]

        response = self.client.post(reverse('customer_shift'), {
            'campaign_id': self.campaign.id,
            'destination_telecaller_id': self.inactive_tc.id,
            'customer_ids': [customer_to_shift.id]
        })

        link = CampaignCustomer.objects.get(campaign=self.campaign, customer=customer_to_shift)
        self.assertEqual(link.assigned_telecaller, self.tc1)

    def test_09_same_source_destination_shift_is_rejected(self):
        """9. Shifting to the same tele-caller is rejected."""
        customer_to_shift = self.assigned_customers[0]

        response = self.client.post(reverse('customer_shift'), {
            'campaign_id': self.campaign.id,
            'destination_telecaller_id': self.tc1.id,
            'customer_ids': [customer_to_shift.id]
        })

        link = CampaignCustomer.objects.get(campaign=self.campaign, customer=customer_to_shift)
        self.assertEqual(link.assigned_telecaller, self.tc1)

    def test_10_historical_call_ownership_remains_unchanged_after_shift(self):
        """10. Critical rule: Shifting customer does NOT rewrite historical call ownership."""
        customer_to_shift = self.assigned_customers[0]

        # TC1 makes Call #10 on this customer
        call_10 = CallRecord.objects.create(
            campaign=self.campaign,
            customer=customer_to_shift,
            telecaller=self.tc1,
            call_status='Completed',
            call_start_time=timezone.now() - timezone.timedelta(minutes=10),
            call_end_time=timezone.now() - timezone.timedelta(minutes=8),
            duration=120,
            comments='Original initial contact call by TC1'
        )

        # Admin shifts customer to TC2
        self.client.post(reverse('customer_shift'), {
            'campaign_id': self.campaign.id,
            'destination_telecaller_id': self.tc2.id,
            'customer_ids': [customer_to_shift.id]
        })

        # Future assignment is now TC2
        link = CampaignCustomer.objects.get(campaign=self.campaign, customer=customer_to_shift)
        self.assertEqual(link.assigned_telecaller, self.tc2)

        # Historical Call #10 is still TC1
        call_10.refresh_from_db()
        self.assertEqual(call_10.telecaller, self.tc1)
        self.assertEqual(call_10.comments, 'Original initial contact call by TC1')

        # No duplicate CampaignCustomer records
        self.assertEqual(
            CampaignCustomer.objects.filter(campaign=self.campaign, customer=customer_to_shift).count(),
            1
        )


class MentorFeedbackQuestionnaireTests(TestCase):
    """
    Mentor Feedback Regression Tests: Questionnaire in Call Console
    Tests 11 to 21
    """
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin_quest',
            email='admin_q@test.com',
            password='Password123!',
            role='ADMIN'
        )
        self.tc1 = User.objects.create_user(
            username='tc_quest1',
            email='tcq1@test.com',
            password='Password123!',
            role='TELE_CALLER',
            is_active=True
        )
        self.tc2 = User.objects.create_user(
            username='tc_quest2',
            email='tcq2@test.com',
            password='Password123!',
            role='TELE_CALLER',
            is_active=True
        )
        self.campaign = Campaign.objects.create(
            name='Customer Satisfaction Campaign',
            status='Active',
            start_date=timezone.now().date(),
            end_date=(timezone.now() + timezone.timedelta(days=30)).date(),
            created_by=self.admin
        )
        self.questionnaire = Questionnaire.objects.create(
            campaign=self.campaign,
            title='CSAT Feedback Script',
            created_by=self.admin
        )

        # Render all 5 supported question types
        self.q_single = Question.objects.create(
            questionnaire=self.questionnaire,
            question_text='Preferred communication channel?',
            question_type='single_choice',
            options=['Email', 'Phone', 'WhatsApp'],
            required=True,
            order=1
        )
        self.q_multi = Question.objects.create(
            questionnaire=self.questionnaire,
            question_text='Interested solutions?',
            question_type='multiple_choice',
            options=['Cloud ERP', 'CRM Portal', 'Analytics Engine'],
            required=True,
            order=2
        )
        self.q_rating = Question.objects.create(
            questionnaire=self.questionnaire,
            question_text='Rate our responsiveness (1-5)?',
            question_type='rating_scale',
            required=True,
            order=3
        )
        self.q_open = Question.objects.create(
            questionnaire=self.questionnaire,
            question_text='Any specific pain points?',
            question_type='open_ended',
            required=False,
            order=4
        )
        self.q_yesno = Question.objects.create(
            questionnaire=self.questionnaire,
            question_text='Are you the key decision maker?',
            question_type='yes_no',
            required=True,
            order=5
        )

        self.cust_a = Customer.objects.create(name='Alice Wonder', phone='+15551234567', is_active=True)
        self.cust_b = Customer.objects.create(name='Bob Builder', phone='+15557654321', is_active=True)

        self.assign_a = CampaignCustomer.objects.create(
            campaign=self.campaign,
            customer=self.cust_a,
            assigned_telecaller=self.tc1,
            assignment_status='Assigned'
        )
        self.assign_b = CampaignCustomer.objects.create(
            campaign=self.campaign,
            customer=self.cust_b,
            assigned_telecaller=self.tc2,
            assignment_status='Assigned'
        )

        self.client.force_login(self.tc1)

    def test_11_correct_campaign_questionnaire_appears_in_call_console(self):
        """11. Correct campaign questionnaire appears in live Call Console."""
        response = self.client.get(reverse('record_call', kwargs={'assignment_id': self.assign_a.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['questionnaire'], self.questionnaire)
        self.assertEqual(len(response.context['questions']), 5)
        self.assertContains(response, 'Preferred communication channel?')
        self.assertContains(response, 'Interested solutions?')
        self.assertContains(response, 'Rate our responsiveness (1-5)?')
        self.assertContains(response, 'Any specific pain points?')
        self.assertContains(response, 'Are you the key decision maker?')

    def test_12_single_choice_answer_saves(self):
        """12. Single-choice answer saves correctly in QuestionResponse."""
        data = {
            'call_status': 'Completed',
            'duration': '45',
            'comments': 'Good discussion with lead',
            f'question_{self.q_single.id}': 'WhatsApp',
            f'question_{self.q_multi.id}': ['Cloud ERP'],
            f'question_{self.q_rating.id}': '4',
            f'question_{self.q_yesno.id}': 'Yes'
        }
        response = self.client.post(reverse('record_call', kwargs={'assignment_id': self.assign_a.pk}), data)
        self.assertEqual(response.status_code, 302)

        resp = QuestionResponse.objects.filter(question=self.q_single).first()
        self.assertIsNotNone(resp)
        self.assertIn('WhatsApp', resp.selected_options)

    def test_13_multiple_choice_answer_saves(self):
        """13. Multiple-choice answer saves correctly."""
        data = {
            'call_status': 'Completed',
            'duration': '50',
            f'question_{self.q_single.id}': 'Email',
            f'question_{self.q_multi.id}': ['Cloud ERP', 'Analytics Engine'],
            f'question_{self.q_rating.id}': '5',
            f'question_{self.q_yesno.id}': 'Yes'
        }
        response = self.client.post(reverse('record_call', kwargs={'assignment_id': self.assign_a.pk}), data)
        self.assertEqual(response.status_code, 302)

        resp = QuestionResponse.objects.filter(question=self.q_multi).first()
        self.assertIsNotNone(resp)
        self.assertIn('Cloud ERP', resp.selected_options)
        self.assertIn('Analytics Engine', resp.selected_options)

    def test_14_rating_answer_saves(self):
        """14. Rating scale answer saves correctly as integer 1-5."""
        data = {
            'call_status': 'Completed',
            'duration': '35',
            f'question_{self.q_single.id}': 'Phone',
            f'question_{self.q_multi.id}': ['CRM Portal'],
            f'question_{self.q_rating.id}': '5',
            f'question_{self.q_yesno.id}': 'Yes'
        }
        response = self.client.post(reverse('record_call', kwargs={'assignment_id': self.assign_a.pk}), data)
        self.assertEqual(response.status_code, 302)

        resp = QuestionResponse.objects.filter(question=self.q_rating).first()
        self.assertIsNotNone(resp)
        self.assertEqual(resp.rating, 5)

    def test_15_open_ended_answer_saves(self):
        """15. Open-ended answer saves correctly as text."""
        data = {
            'call_status': 'Completed',
            'duration': '60',
            f'question_{self.q_single.id}': 'Phone',
            f'question_{self.q_multi.id}': ['CRM Portal'],
            f'question_{self.q_rating.id}': '3',
            f'question_{self.q_open.id}': 'Client requests migration support for on-prem DB.',
            f'question_{self.q_yesno.id}': 'Yes'
        }
        response = self.client.post(reverse('record_call', kwargs={'assignment_id': self.assign_a.pk}), data)
        self.assertEqual(response.status_code, 302)

        resp = QuestionResponse.objects.filter(question=self.q_open).first()
        self.assertIsNotNone(resp)
        self.assertEqual(resp.response_text, 'Client requests migration support for on-prem DB.')

    def test_16_yes_no_answer_saves(self):
        """16. Yes/No answer saves correctly."""
        data = {
            'call_status': 'Completed',
            'duration': '40',
            f'question_{self.q_single.id}': 'Email',
            f'question_{self.q_multi.id}': ['Cloud ERP'],
            f'question_{self.q_rating.id}': '4',
            f'question_{self.q_yesno.id}': 'No'
        }
        response = self.client.post(reverse('record_call', kwargs={'assignment_id': self.assign_a.pk}), data)
        self.assertEqual(response.status_code, 302)

        resp = QuestionResponse.objects.filter(question=self.q_yesno).first()
        self.assertIsNotNone(resp)
        self.assertIn('No', resp.selected_options)

    def test_17_required_question_validation_works_server_side(self):
        """17. Server-side validation catches missing required questionnaire answers."""
        # Omit required rating question
        data = {
            'call_status': 'Completed',
            'duration': '30',
            f'question_{self.q_single.id}': 'Email',
            f'question_{self.q_multi.id}': ['Cloud ERP'],
            # missing question_rating!
            f'question_{self.q_yesno.id}': 'Yes'
        }
        response = self.client.post(reverse('record_call', kwargs={'assignment_id': self.assign_a.pk}), data)
        self.assertEqual(response.status_code, 200)

        # CallRecord must NOT be created due to validation failure
        self.assertFalse(CallRecord.objects.filter(customer=self.cust_a).exists())

    def test_18_responses_are_linked_to_correct_call_record(self):
        """18. QuestionResponse records are linked to the correct CallRecord."""
        data = {
            'call_status': 'Completed',
            'duration': '55',
            f'question_{self.q_single.id}': 'WhatsApp',
            f'question_{self.q_multi.id}': ['Cloud ERP'],
            f'question_{self.q_rating.id}': '4',
            f'question_{self.q_yesno.id}': 'Yes'
        }
        self.client.post(reverse('record_call', kwargs={'assignment_id': self.assign_a.pk}), data)

        call_rec = CallRecord.objects.filter(customer=self.cust_a).first()
        self.assertIsNotNone(call_rec)

        resps = QuestionResponse.objects.filter(call_record=call_rec)
        self.assertEqual(resps.count(), 4)
        for r in resps:
            self.assertEqual(r.call_record, call_rec)

    def test_19_responses_cannot_leak_between_customers(self):
        """19. Responses cannot leak between customers or tele-callers."""
        # 1. Complete call for Customer A
        data = {
            'call_status': 'Completed',
            'duration': '50',
            f'question_{self.q_single.id}': 'WhatsApp',
            f'question_{self.q_multi.id}': ['Cloud ERP'],
            f'question_{self.q_rating.id}': '5',
            f'question_{self.q_yesno.id}': 'Yes'
        }
        self.client.post(reverse('record_call', kwargs={'assignment_id': self.assign_a.pk}), data)
        call_rec_a = CallRecord.objects.filter(customer=self.cust_a).first()

        # 2. TC2 logs in and attempts to access Customer A's assignment console
        self.client.force_login(self.tc2)
        tamper_response = self.client.get(reverse('record_call', kwargs={'assignment_id': self.assign_a.pk}))
        # TC2 is blocked from accessing Customer A's console
        self.assertEqual(tamper_response.status_code, 302)

        # 3. Customer A's responses belong strictly to CallRecord A
        for resp in QuestionResponse.objects.filter(call_record=call_rec_a):
            self.assertEqual(resp.call_record.customer, self.cust_a)

    def test_20_duplicate_response_for_same_question_call_is_prevented(self):
        """20. Database-level UniqueConstraint prevents duplicate responses for same question in a call."""
        call_rec = CallRecord.objects.create(
            campaign=self.campaign,
            customer=self.cust_a,
            telecaller=self.tc1,
            call_status='Completed',
            call_start_time=timezone.now(),
            duration=30
        )
        QuestionResponse.objects.create(
            call_record=call_rec,
            question=self.q_single,
            response_text='Email'
        )

        with self.assertRaises(IntegrityError):
            QuestionResponse.objects.create(
                call_record=call_rec,
                question=self.q_single,
                response_text='Phone'
            )

    def test_21_existing_call_workflow_continues_to_work(self):
        """21. Existing live call workflow (timer, outcome, follow-up, comments, assignment update) works seamlessly."""
        tomorrow = (timezone.now() + timezone.timedelta(days=1)).date()
        data = {
            'call_status': 'Completed',
            'duration': '125',
            'comments': 'Customer agreed to presentation. Followup scheduled.',
            'schedule_followup': 'on',
            'followup_date': tomorrow.strftime('%Y-%m-%d'),
            'followup_time': '14:30',
            'followup_notes': 'Demo presentation with team',
            f'question_{self.q_single.id}': 'Phone',
            f'question_{self.q_multi.id}': ['Cloud ERP', 'Analytics Engine'],
            f'question_{self.q_rating.id}': '5',
            f'question_{self.q_yesno.id}': 'Yes'
        }
        response = self.client.post(reverse('record_call', kwargs={'assignment_id': self.assign_a.pk}), data)
        self.assertEqual(response.status_code, 302)

        # Verify CallRecord
        call_rec = CallRecord.objects.filter(customer=self.cust_a).first()
        self.assertIsNotNone(call_rec)
        self.assertEqual(call_rec.duration, 125)
        self.assertEqual(call_rec.call_status, 'Completed')
        self.assertEqual(call_rec.comments, 'Customer agreed to presentation. Followup scheduled.')

        # Verify Assignment status transition
        self.assign_a.refresh_from_db()
        self.assertEqual(self.assign_a.assignment_status, 'Completed')

        # Verify Follow-up creation
        fu = FollowUp.objects.filter(customer=self.cust_a, scheduled_date=tomorrow).first()
        self.assertIsNotNone(fu)
        self.assertEqual(fu.assigned_to, self.tc1)
        self.assertEqual(fu.notes, 'Demo presentation with team')

        # Verify Notification
        notif = Notification.objects.filter(recipient=self.tc1, notification_type='followup').first()
        self.assertIsNotNone(notif)
