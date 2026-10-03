"""
Regression tests for CCM Call Queue / Assignment Status UX Fix.
Tests cover:
1. Completed assignment does not appear as "Start Call"
2. Completed assignment with pending follow-up appears as a follow-up task
3. Completed assignment without pending follow-up is not actionable
4. Start Call cannot bypass completed-assignment protection
5. Follow-up call can be started when assignment is still open
6. Dashboard KPI counts are correct
7. Campaign counters have correct definitions
8. Tele-caller sidebar contains only tele-caller features
9. Admin sidebar contains admin features
"""
from django.test import TestCase, Client
from django.urls import reverse
from datetime import date, time, timedelta
from django.utils import timezone

from accounts.models import User
from campaigns.models import Campaign, Questionnaire, Question
from customers.models import Customer, CampaignCustomer
from calls.models import CallRecord, FollowUp
from analytics.models import Notification


class TaskQueueTests(TestCase):
    """Tests for the telecaller dashboard 'My Next Tasks' logic."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin_tq', password='password123', role='ADMIN'
        )
        self.telecaller = User.objects.create_user(
            username='tc_tq', password='password123', role='TELE_CALLER',
            first_name='Rahul', last_name='Tester'
        )

        self.campaign = Campaign.objects.create(
            name='Queue Test Campaign',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status='Active',
            target_calls=100,
            created_by=self.admin
        )

        # Customer A: Completed assignment, NO pending follow-up
        self.cust_a = Customer.objects.create(name='Customer A', phone='+10001')
        self.assign_a = CampaignCustomer.objects.create(
            campaign=self.campaign, customer=self.cust_a,
            assigned_telecaller=self.telecaller,
            assignment_status='Completed'
        )
        self.call_a = CallRecord.objects.create(
            campaign=self.campaign, customer=self.cust_a,
            telecaller=self.telecaller, call_status='Completed',
            call_start_time=timezone.now() - timedelta(hours=1),
            call_end_time=timezone.now(), duration=120
        )

        # Customer B: Completed assignment, WITH pending follow-up
        self.cust_b = Customer.objects.create(name='Customer B', phone='+10002')
        self.assign_b = CampaignCustomer.objects.create(
            campaign=self.campaign, customer=self.cust_b,
            assigned_telecaller=self.telecaller,
            assignment_status='Completed'
        )
        self.call_b = CallRecord.objects.create(
            campaign=self.campaign, customer=self.cust_b,
            telecaller=self.telecaller, call_status='Follow-up Required',
            call_start_time=timezone.now() - timedelta(hours=2),
            call_end_time=timezone.now() - timedelta(hours=1), duration=60
        )
        self.followup_b = FollowUp.objects.create(
            call_record=self.call_b, customer=self.cust_b,
            assigned_to=self.telecaller,
            scheduled_date=date.today(),
            scheduled_time=time(10, 0),
            status='Pending', notes='Call back'
        )

        # Customer C: Pending assignment (new lead)
        self.cust_c = Customer.objects.create(name='Customer C', phone='+10003')
        self.assign_c = CampaignCustomer.objects.create(
            campaign=self.campaign, customer=self.cust_c,
            assigned_telecaller=self.telecaller,
            assignment_status='Assigned'
        )

        # Customer D: In Progress assignment
        self.cust_d = Customer.objects.create(name='Customer D', phone='+10004')
        self.assign_d = CampaignCustomer.objects.create(
            campaign=self.campaign, customer=self.cust_d,
            assigned_telecaller=self.telecaller,
            assignment_status='In Progress'
        )

        self.client.login(username='tc_tq', password='password123')

    def test_completed_assignment_without_followup_not_in_tasks(self):
        """Customer A: Completed, no follow-up → NOT in task queue."""
        response = self.client.get(reverse('dashboard'))
        tasks = response.context['next_tasks']
        task_customers = [t['customer'].pk for t in tasks]
        self.assertNotIn(self.cust_a.pk, task_customers)

    def test_completed_assignment_with_followup_appears_as_followup_task(self):
        """Customer B: Completed but has pending follow-up → appears as follow-up task."""
        response = self.client.get(reverse('dashboard'))
        tasks = response.context['next_tasks']
        b_tasks = [t for t in tasks if t['customer'].pk == self.cust_b.pk]
        self.assertEqual(len(b_tasks), 1)
        task = b_tasks[0]
        self.assertEqual(task['task'], 'Follow-up Callback')
        self.assertIn(task['task_type'], ('followup_call', 'followup_only'))
        # Since assignment is Completed, action should NOT be 'Start Call'
        self.assertNotEqual(task['action_label'], 'Start Call')

    def test_completed_assignment_followup_action_is_handle_followup(self):
        """Customer B: Completed assignment → action should be 'Handle Follow-up'."""
        response = self.client.get(reverse('dashboard'))
        tasks = response.context['next_tasks']
        b_tasks = [t for t in tasks if t['customer'].pk == self.cust_b.pk]
        self.assertEqual(len(b_tasks), 1)
        task = b_tasks[0]
        self.assertEqual(task['task_type'], 'followup_only')
        self.assertEqual(task['action_label'], 'Handle Follow-up')

    def test_pending_assignment_appears_as_start_call(self):
        """Customer C: Assigned → appears with 'Start Call' action."""
        response = self.client.get(reverse('dashboard'))
        tasks = response.context['next_tasks']
        c_tasks = [t for t in tasks if t['customer'].pk == self.cust_c.pk]
        self.assertEqual(len(c_tasks), 1)
        task = c_tasks[0]
        self.assertEqual(task['task_type'], 'new_call')
        self.assertEqual(task['action_label'], 'Start Call')

    def test_in_progress_assignment_appears_as_continue_call(self):
        """Customer D: In Progress → appears with 'Continue Call' action."""
        response = self.client.get(reverse('dashboard'))
        tasks = response.context['next_tasks']
        d_tasks = [t for t in tasks if t['customer'].pk == self.cust_d.pk]
        self.assertEqual(len(d_tasks), 1)
        task = d_tasks[0]
        self.assertEqual(task['task_type'], 'new_call')
        self.assertEqual(task['action_label'], 'Continue Call')

    def test_start_call_rejected_for_completed_assignment(self):
        """Backend still rejects record_call on a completed assignment."""
        response = self.client.get(
            reverse('record_call', kwargs={'assignment_id': self.assign_a.pk})
        )
        self.assertRedirects(
            response,
            reverse('campaign_detail', kwargs={'pk': self.campaign.pk})
        )

    def test_followup_call_allowed_for_open_assignment(self):
        """If assignment is still Assigned/In Progress with a follow-up,
        the follow-up task should allow starting a call."""
        # Reopen Customer B's assignment
        self.assign_b.assignment_status = 'In Progress'
        self.assign_b.save()

        response = self.client.get(reverse('dashboard'))
        tasks = response.context['next_tasks']
        b_tasks = [t for t in tasks if t['customer'].pk == self.cust_b.pk]
        self.assertEqual(len(b_tasks), 1)
        task = b_tasks[0]
        self.assertEqual(task['task_type'], 'followup_call')
        self.assertEqual(task['action_label'], 'Start Follow-up Call')
        self.assertEqual(task['assignment_pk'], self.assign_b.pk)


class DashboardKPITests(TestCase):
    """Tests for telecaller dashboard KPI definitions."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin_kpi', password='password123', role='ADMIN'
        )
        self.telecaller = User.objects.create_user(
            username='tc_kpi', password='password123', role='TELE_CALLER'
        )

        self.campaign = Campaign.objects.create(
            name='KPI Campaign',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status='Active',
            target_calls=50,
            created_by=self.admin
        )

        # 2 pending assignments
        for i in range(2):
            cust = Customer.objects.create(name=f'KPI Cust {i}', phone=f'+2000{i}')
            CampaignCustomer.objects.create(
                campaign=self.campaign, customer=cust,
                assigned_telecaller=self.telecaller,
                assignment_status='Assigned'
            )

        # 1 completed assignment
        cust_done = Customer.objects.create(name='KPI Done', phone='+20009')
        CampaignCustomer.objects.create(
            campaign=self.campaign, customer=cust_done,
            assigned_telecaller=self.telecaller,
            assignment_status='Completed'
        )
        CallRecord.objects.create(
            campaign=self.campaign, customer=cust_done,
            telecaller=self.telecaller, call_status='Completed',
            call_start_time=timezone.now(), duration=60
        )

        # 1 follow-up
        call_fu = CallRecord.objects.create(
            campaign=self.campaign, customer=cust_done,
            telecaller=self.telecaller, call_status='Follow-up Required',
            call_start_time=timezone.now(), duration=30
        )
        FollowUp.objects.create(
            call_record=call_fu, customer=cust_done,
            assigned_to=self.telecaller,
            scheduled_date=date.today(),
            scheduled_time=time(14, 0),
            status='Pending'
        )

        self.client.login(username='tc_kpi', password='password123')

    def test_pending_assignments_kpi(self):
        """calls_pending = count of Assigned/In Progress assignments."""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['calls_pending'], 2)

    def test_followups_due_kpi(self):
        """followups_due = count of Pending/Overdue follow-ups."""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['followups_due'], 1)

    def test_calls_completed_kpi(self):
        """calls_completed = total completed CallRecords for this telecaller."""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['calls_completed'], 1)


class CampaignDetailCounterTests(TestCase):
    """Tests for campaign detail page counter definitions."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin_cd', password='password123', role='ADMIN'
        )
        self.telecaller = User.objects.create_user(
            username='tc_cd', password='password123', role='TELE_CALLER'
        )

        self.campaign = Campaign.objects.create(
            name='Counter Campaign',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status='Active',
            target_calls=20,
            created_by=self.admin
        )

        self.cust1 = Customer.objects.create(name='Counter C1', phone='+30001')
        self.assign1 = CampaignCustomer.objects.create(
            campaign=self.campaign, customer=self.cust1,
            assigned_telecaller=self.telecaller,
            assignment_status='Completed'
        )
        # Multiple completed calls for same customer (valid business scenario)
        for i in range(3):
            CallRecord.objects.create(
                campaign=self.campaign, customer=self.cust1,
                telecaller=self.telecaller, call_status='Completed',
                call_start_time=timezone.now(), duration=60
            )
        # One follow-up call
        call_fu = CallRecord.objects.create(
            campaign=self.campaign, customer=self.cust1,
            telecaller=self.telecaller, call_status='Follow-up Required',
            call_start_time=timezone.now(), duration=30
        )
        FollowUp.objects.create(
            call_record=call_fu, customer=self.cust1,
            assigned_to=self.telecaller,
            scheduled_date=date.today(), scheduled_time=time(15, 0),
            status='Pending'
        )

        self.cust2 = Customer.objects.create(name='Counter C2', phone='+30002')
        self.assign2 = CampaignCustomer.objects.create(
            campaign=self.campaign, customer=self.cust2,
            assigned_telecaller=self.telecaller,
            assignment_status='Assigned'
        )

        self.client.login(username='admin_cd', password='password123')

    def test_completed_calls_can_exceed_customers(self):
        """completed_calls counts CallRecords, so it can exceed total_customers."""
        response = self.client.get(
            reverse('campaign_detail', kwargs={'pk': self.campaign.pk})
        )
        self.assertEqual(response.context['completed_calls'], 3)
        self.assertEqual(response.context['total_customers'], 2)
        # completed_calls > total_customers is valid

    def test_completed_assignments_cannot_exceed_total_customers(self):
        """completed_assignments must be <= total_customers."""
        response = self.client.get(
            reverse('campaign_detail', kwargs={'pk': self.campaign.pk})
        )
        completed_assignments = response.context['completed_assignments']
        total_customers = response.context['total_customers']
        self.assertLessEqual(completed_assignments, total_customers)
        self.assertEqual(completed_assignments, 1)

    def test_call_records_count_is_total_calls(self):
        """call_records_count = total call records for this campaign."""
        response = self.client.get(
            reverse('campaign_detail', kwargs={'pk': self.campaign.pk})
        )
        self.assertEqual(response.context['call_records_count'], 4)

    def test_followups_count_is_campaign_specific(self):
        """followups_count counts follow-ups linked to this campaign's call records."""
        response = self.client.get(
            reverse('campaign_detail', kwargs={'pk': self.campaign.pk})
        )
        self.assertEqual(response.context['followups_count'], 1)

    def test_pending_assignments_is_not_completed(self):
        """pending_calls = assignments with Assigned/In Progress/Unassigned status."""
        response = self.client.get(
            reverse('campaign_detail', kwargs={'pk': self.campaign.pk})
        )
        self.assertEqual(response.context['pending_calls'], 1)  # Only cust2


class SidebarRBACTests(TestCase):
    """Tests for role-based sidebar navigation."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin_sb', password='password123', role='ADMIN'
        )
        self.telecaller = User.objects.create_user(
            username='tc_sb', password='password123', role='TELE_CALLER'
        )

    def test_telecaller_sidebar_has_correct_items(self):
        """Telecaller sees: Dashboard, My Campaigns, My Customers, My Calls, My Follow-ups, Notifications."""
        self.client.login(username='tc_sb', password='password123')
        response = self.client.get(reverse('dashboard'))
        content = response.content.decode()
        self.assertIn('Dashboard', content)
        self.assertIn('My Campaigns', content)
        self.assertIn('My Customers', content)
        self.assertIn('My Calls', content)
        self.assertIn('My Follow-ups', content)
        self.assertIn('Notifications', content)

    def test_telecaller_sidebar_does_not_have_admin_items(self):
        """Telecaller does NOT see: Analytics, Reports, Tele-callers management."""
        self.client.login(username='tc_sb', password='password123')
        response = self.client.get(reverse('dashboard'))
        content = response.content.decode()
        # Sidebar should not contain admin-only nav items
        self.assertNotIn('Analytics', content)
        self.assertNotIn('Reports', content)
        # 'Tele-callers' as a nav item only appears for admin
        # (The word 'Tele-caller' appears in footer role display, but the nav link text is 'Tele-callers')
        self.assertNotIn('Insights & Management', content)

    def test_admin_sidebar_has_admin_items(self):
        """Admin sees: Dashboard, Campaigns, Customers, Tele-callers, Call Records, Follow-ups, Analytics, Reports."""
        self.client.login(username='admin_sb', password='password123')
        response = self.client.get(reverse('dashboard'))
        content = response.content.decode()
        self.assertIn('Dashboard', content)
        self.assertIn('Campaigns', content)
        self.assertIn('Customers', content)
        self.assertIn('Tele-callers', content)
        self.assertIn('Call Records', content)
        self.assertIn('Follow-ups', content)
        self.assertIn('Analytics', content)
        self.assertIn('Reports', content)
        self.assertIn('Insights & Management', content)
