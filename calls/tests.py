from django.test import TestCase, Client
from django.urls import reverse
from datetime import date, timedelta
from django.utils import timezone
from accounts.models import User
from campaigns.models import Campaign, Questionnaire, Question
from customers.models import Customer, CampaignCustomer
from calls.models import CallRecord, FollowUp, QuestionResponse

class CallWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username='admin_call', password='password123', role='ADMIN')
        self.telecaller = User.objects.create_user(username='tc_call', password='password123', role='TELE_CALLER')
        self.client.login(username='tc_call', password='password123')

        self.campaign = Campaign.objects.create(
            name='Call Test Campaign',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            status='Active',
            created_by=self.admin
        )
        self.customer = Customer.objects.create(name='Call Lead', phone='+15558800')
        self.assignment = CampaignCustomer.objects.create(
            campaign=self.campaign,
            customer=self.customer,
            assigned_telecaller=self.telecaller,
            assignment_status='Assigned'
        )

        self.questionnaire = Questionnaire.objects.create(campaign=self.campaign, title='Call Survey', created_by=self.admin)
        self.q1 = Question.objects.create(questionnaire=self.questionnaire, question_text='Satisfied?', question_type='yes_no', order=1)

    def test_record_call_completed_with_responses(self):
        response = self.client.post(reverse('record_call', kwargs={'assignment_id': self.assignment.id}), {
            'call_status': 'Completed',
            'duration': '120',
            'comments': 'Great call conversation',
            f'question_{self.q1.id}': 'Yes'
        })
        self.assertEqual(CallRecord.objects.filter(customer=self.customer).count(), 1)
        call_rec = CallRecord.objects.get(customer=self.customer)
        self.assertEqual(call_rec.call_status, 'Completed')
        self.assertEqual(QuestionResponse.objects.filter(call_record=call_rec).count(), 1)

    def test_followup_scheduling(self):
        response = self.client.post(reverse('record_call', kwargs={'assignment_id': self.assignment.id}), {
            'call_status': 'Follow-up Required',
            'duration': '15',
            'comments': 'Customer asked for callback',
            'schedule_followup': 'on',
            'followup_date': str(date.today() + timedelta(days=1)),
            'followup_time': '10:00',
            'followup_notes': 'Morning callback'
        })
        self.assertEqual(FollowUp.objects.filter(customer=self.customer).count(), 1)

    def test_unassigned_customer_call_record_blocked(self):
        other_telecaller = User.objects.create_user(username='other_tc', password='password123', role='TELE_CALLER')
        other_assignment = CampaignCustomer.objects.create(
            campaign=self.campaign,
            customer=Customer.objects.create(name='Other Customer', phone='+15559988'),
            assigned_telecaller=other_telecaller,
            assignment_status='Assigned'
        )
        response = self.client.get(reverse('record_call', kwargs={'assignment_id': other_assignment.id}))
        self.assertRedirects(response, reverse('customer_list'))

    def test_inactive_campaign_call_record_blocked(self):
        self.campaign.status = 'Draft'
        self.campaign.save()
        response = self.client.get(reverse('record_call', kwargs={'assignment_id': self.assignment.id}))
        self.assertRedirects(response, reverse('campaign_detail', kwargs={'pk': self.campaign.id}))

    def test_completed_assignment_call_record_blocked(self):
        self.assignment.assignment_status = 'Completed'
        self.assignment.save()
        response = self.client.get(reverse('record_call', kwargs={'assignment_id': self.assignment.id}))
        self.assertRedirects(response, reverse('campaign_detail', kwargs={'pk': self.campaign.id}))

    def test_required_question_validation_prevents_save(self):
        response = self.client.post(reverse('record_call', kwargs={'assignment_id': self.assignment.id}), {
            'call_status': 'Completed',
            'duration': '60',
            'comments': 'Incomplete response',
            # omitted question_1 which is required
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CallRecord.objects.filter(customer=self.customer).count(), 0)

    def test_overdue_followup_status_update(self):
        from calls.views import update_overdue_followups
        past_date = date.today() - timedelta(days=2)
        fu = FollowUp.objects.create(
            customer=self.customer,
            assigned_to=self.telecaller,
            scheduled_date=past_date,
            scheduled_time='10:00:00',
            status='Pending'
        )
        update_overdue_followups(self.telecaller)
        fu.refresh_from_db()
        self.assertEqual(fu.status, 'Overdue')

    def test_call_success_view_with_next_assignment(self):
        # Create second lead for next assignment test
        cust2 = Customer.objects.create(name='Lead Two', phone='+15550002')
        assign2 = CampaignCustomer.objects.create(
            campaign=self.campaign,
            customer=cust2,
            assigned_telecaller=self.telecaller,
            assignment_status='Assigned'
        )
        call_rec = CallRecord.objects.create(
            campaign=self.campaign,
            customer=self.customer,
            telecaller=self.telecaller,
            call_status='Completed',
            call_start_time=timezone.now(),
            duration=45
        )
        response = self.client.get(reverse('call_success', kwargs={'call_id': call_rec.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['next_assignment'].id, assign2.id)

    def test_call_success_permission_denied_for_other_telecaller(self):
        other_tc = User.objects.create_user(username='tc_other', password='password123', role='TELE_CALLER')
        call_rec = CallRecord.objects.create(
            campaign=self.campaign,
            customer=self.customer,
            telecaller=other_tc,
            call_status='Completed',
            call_start_time=timezone.now(),
            duration=30
        )
        response = self.client.get(reverse('call_success', kwargs={'call_id': call_rec.id}))
        self.assertRedirects(response, reverse('dashboard'))

    def test_followup_cancel(self):
        fu = FollowUp.objects.create(
            customer=self.customer,
            assigned_to=self.telecaller,
            scheduled_date=date.today() + timedelta(days=2),
            scheduled_time='14:00:00',
            status='Pending'
        )
        response = self.client.post(reverse('followup_cancel', kwargs={'pk': fu.id}))
        self.assertRedirects(response, reverse('followup_list'))
        fu.refresh_from_db()
        self.assertEqual(fu.status, 'Cancelled')

    def test_followup_complete(self):
        fu = FollowUp.objects.create(
            customer=self.customer,
            assigned_to=self.telecaller,
            scheduled_date=date.today() + timedelta(days=2),
            scheduled_time='14:00:00',
            status='Pending'
        )
        response = self.client.post(reverse('followup_complete', kwargs={'pk': fu.id}))
        self.assertRedirects(response, reverse('followup_list'))
        fu.refresh_from_db()
        self.assertEqual(fu.status, 'Completed')

