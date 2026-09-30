from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta, time
from accounts.models import User
from campaigns.models import Campaign, Questionnaire, Question
from customers.models import Customer, CampaignCustomer
from calls.models import CallRecord, QuestionResponse, FollowUp
from analytics.models import Notification
from analytics.engine import (
    parse_date_range, get_filtered_calls, compute_call_kpis,
    compute_call_outcome_counts, compute_call_activity_over_time,
    compute_campaign_performance, compute_telecaller_performance,
    compute_questionnaire_analytics, compute_customer_response_insights,
    compute_followup_analytics
)


class AnalyticsAndDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username='admin_dash', password='password123', role='ADMIN')
        self.telecaller = User.objects.create_user(username='tc_dash', password='password123', role='TELE_CALLER')

        self.campaign = Campaign.objects.create(
            name='Dashboard Test Campaign',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            status='Active',
            target_calls=50,
            created_by=self.admin
        )
        self.customer = Customer.objects.create(name='Test Dashboard Lead', phone='+15551234')
        self.assignment = CampaignCustomer.objects.create(
            campaign=self.campaign,
            customer=self.customer,
            assigned_telecaller=self.telecaller,
            assignment_status='Assigned'
        )

    def test_admin_dashboard_metrics_and_context(self):
        self.client.login(username='admin_dash', password='password123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('campaign_progress_list', response.context)
        self.assertIn('action_required_items', response.context)
        self.assertIn('total_campaigns', response.context)
        self.assertIn('calls_completed', response.context)
        self.assertIn('calls_pending', response.context)

    def test_telecaller_dashboard_workload_and_tasks(self):
        self.client.login(username='tc_dash', password='password123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('next_tasks', response.context)
        self.assertIn('calls_pending', response.context)
        self.assertIn('followups_due', response.context)
        tasks = response.context['next_tasks']
        self.assertTrue(any(t['customer'].name == 'Test Dashboard Lead' for t in tasks))

    def test_notification_read_single_redirects_and_marks_read(self):
        self.client.login(username='tc_dash', password='password123')
        notif = Notification.objects.create(
            recipient=self.telecaller,
            title='New Lead Assigned',
            message='You have a new customer assigned.',
            related_object_type='customer',
            related_object_id=self.customer.id
        )
        url = reverse('notification_read_single', kwargs={'pk': notif.id})
        response = self.client.get(url)
        self.assertRedirects(response, reverse('customer_detail', kwargs={'pk': self.customer.id}))
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_notification_read_all(self):
        self.client.login(username='tc_dash', password='password123')
        Notification.objects.create(recipient=self.telecaller, title='N1', message='M1')
        Notification.objects.create(recipient=self.telecaller, title='N2', message='M2')
        response = self.client.post(reverse('notification_read_all'))
        self.assertRedirects(response, reverse('notification_list'))
        self.assertEqual(Notification.objects.filter(recipient=self.telecaller, is_read=False).count(), 0)


class AdvancedAnalyticsAndReportingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username='admin_adv', password='password123', role='ADMIN')
        self.tc1 = User.objects.create_user(username='tc_alpha', password='password123', role='TELE_CALLER', first_name='Alpha')
        self.tc2 = User.objects.create_user(username='tc_beta', password='password123', role='TELE_CALLER', first_name='Beta')

        # Create campaigns
        self.camp1 = Campaign.objects.create(
            name='Alpha Marketing',
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() + timedelta(days=20),
            status='Active',
            target_calls=10,
            created_by=self.admin
        )
        self.camp2 = Campaign.objects.create(
            name='Beta Outreach',
            start_date=date.today() - timedelta(days=5),
            end_date=date.today() + timedelta(days=15),
            status='Active',
            target_calls=20,
            created_by=self.admin
        )

        # Create customers
        self.cust1 = Customer.objects.create(name='Lead One', phone='+19990001')
        self.cust2 = Customer.objects.create(name='Lead Two', phone='+19990002')
        self.cust3 = Customer.objects.create(name='Lead Three', phone='+19990003')

        # Assign customers
        CampaignCustomer.objects.create(campaign=self.camp1, customer=self.cust1, assigned_telecaller=self.tc1, assignment_status='Completed')
        CampaignCustomer.objects.create(campaign=self.camp1, customer=self.cust2, assigned_telecaller=self.tc1, assignment_status='Assigned')
        CampaignCustomer.objects.create(campaign=self.camp2, customer=self.cust3, assigned_telecaller=self.tc2, assignment_status='Assigned')

        # Create call records
        now = timezone.now()
        self.call1 = CallRecord.objects.create(
            campaign=self.camp1, customer=self.cust1, telecaller=self.tc1,
            call_status='Completed', call_start_time=now - timedelta(minutes=10),
            call_end_time=now - timedelta(minutes=5), duration=300
        )
        self.call2 = CallRecord.objects.create(
            campaign=self.camp1, customer=self.cust2, telecaller=self.tc1,
            call_status='No Answer', call_start_time=now - timedelta(minutes=30),
            call_end_time=now - timedelta(minutes=29), duration=60
        )
        self.call3 = CallRecord.objects.create(
            campaign=self.camp2, customer=self.cust3, telecaller=self.tc2,
            call_status='Follow-up Required', call_start_time=now - timedelta(hours=2),
            call_end_time=now - timedelta(hours=2, minutes=-2), duration=120
        )

        # Questionnaire setup
        self.questionnaire = Questionnaire.objects.create(
            campaign=self.camp1, title='Alpha Feedback', created_by=self.admin
        )
        self.q_choice = Question.objects.create(
            questionnaire=self.questionnaire,
            question_text='Preferred contact tool?',
            question_type='single_choice',
            options=['Email', 'Phone', 'WhatsApp'],
            order=1
        )
        self.q_rating = Question.objects.create(
            questionnaire=self.questionnaire,
            question_text='Product satisfaction rating?',
            question_type='rating_scale',
            order=2
        )
        self.q_text = Question.objects.create(
            questionnaire=self.questionnaire,
            question_text='Additional suggestions?',
            question_type='open_ended',
            order=3
        )

        # Responses
        QuestionResponse.objects.create(
            call_record=self.call1, question=self.q_choice,
            selected_options=['Email']
        )
        QuestionResponse.objects.create(
            call_record=self.call1, question=self.q_rating,
            rating=5
        )
        QuestionResponse.objects.create(
            call_record=self.call1, question=self.q_text,
            response_text='Excellent service and quick support'
        )

        # Follow-up setup
        self.followup1 = FollowUp.objects.create(
            call_record=self.call3, customer=self.cust3, assigned_to=self.tc2,
            scheduled_date=date.today(), scheduled_time=time(14, 0),
            status='Pending', notes='Call back in afternoon'
        )
        self.followup2 = FollowUp.objects.create(
            call_record=self.call1, customer=self.cust1, assigned_to=self.tc1,
            scheduled_date=date.today() - timedelta(days=2), scheduled_time=time(10, 0),
            status='Overdue', notes='Past due follow up'
        )

    def test_analytics_admin_access(self):
        """Admin can access the analytics dashboard with HTTP 200 and complete context."""
        self.client.login(username='admin_adv', password='password123')
        response = self.client.get(reverse('analytics'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('kpis', response.context)
        self.assertIn('outcome_counts', response.context)
        self.assertIn('campaign_perf', response.context)
        self.assertIn('tc_perf', response.context)
        self.assertIn('fu_analytics', response.context)
        self.assertEqual(response.context['kpis']['total_calls'], 3)
        self.assertEqual(response.context['kpis']['completed_calls'], 1)

    def test_analytics_telecaller_forbidden(self):
        """Tele-caller accessing the analytics dashboard gets HTTP 403."""
        self.client.login(username='tc_alpha', password='password123')
        response = self.client.get(reverse('analytics'))
        self.assertEqual(response.status_code, 403)

    def test_analytics_campaign_filter(self):
        """Filtering by campaign restricts metrics exclusively to that campaign."""
        self.client.login(username='admin_adv', password='password123')
        response = self.client.get(reverse('analytics'), {'campaign': self.camp1.id})
        self.assertEqual(response.status_code, 200)
        kpis = response.context['kpis']
        self.assertEqual(kpis['total_calls'], 2)
        self.assertEqual(kpis['completed_calls'], 1)
        self.assertIn('question_analytics', response.context)
        # camp1 has questionnaire analytics
        q_analytics = response.context['question_analytics']
        self.assertTrue(len(q_analytics) > 0)

    def test_analytics_date_filtering(self):
        """Date range presets correctly filter call data."""
        self.client.login(username='admin_adv', password='password123')
        # Today preset
        resp_today = self.client.get(reverse('analytics'), {'date_range': 'today'})
        self.assertEqual(resp_today.status_code, 200)
        self.assertEqual(resp_today.context['date_label'], 'Today')

        # 7 days preset
        resp_7d = self.client.get(reverse('analytics'), {'date_range': '7days'})
        self.assertEqual(resp_7d.status_code, 200)
        self.assertEqual(resp_7d.context['date_label'], 'Last 7 Days')

        # Custom date range
        today_str = date.today().strftime('%Y-%m-%d')
        resp_custom = self.client.get(reverse('analytics'), {
            'date_range': 'custom',
            'date_from': today_str,
            'date_to': today_str
        })
        self.assertEqual(resp_custom.status_code, 200)
        self.assertEqual(resp_custom.context['date_label'], 'Custom Range')

    def test_kpi_calculations(self):
        """compute_call_kpis accurately calculates rates, durations, and counts."""
        calls_qs = CallRecord.objects.all()
        kpis = compute_call_kpis(calls_qs)
        self.assertEqual(kpis['total_calls'], 3)
        self.assertEqual(kpis['completed_calls'], 1)
        # 1 completed out of 3 = 33.3%
        self.assertEqual(kpis['completion_rate'], 33.3)
        # Completed call duration is 300s = 5m 0s
        self.assertEqual(kpis['avg_duration_sec'], 300)
        self.assertEqual(kpis['avg_duration_fmt'], '5m 0s')
        self.assertEqual(kpis['customers_contacted'], 3)

    def test_call_outcome_aggregation(self):
        """compute_call_outcome_counts aggregates all standard statuses."""
        calls_qs = CallRecord.objects.all()
        counts, total = compute_call_outcome_counts(calls_qs)
        self.assertEqual(total, 3)
        self.assertEqual(counts['Completed']['count'], 1)
        self.assertEqual(counts['No Answer']['count'], 1)
        self.assertEqual(counts['Follow-up Required']['count'], 1)
        self.assertEqual(counts['Busy']['count'], 0)
        self.assertEqual(counts['Unreachable']['count'], 0)
        self.assertAlmostEqual(counts['Completed']['pct'], 33.3, places=1)

    def test_campaign_completion_logic(self):
        """Campaign performance metrics respect target_calls, pending calculations, and capping."""
        perf = compute_campaign_performance()
        alpha_perf = next((p for p in perf if p['campaign'] == self.camp1), None)
        self.assertIsNotNone(alpha_perf)
        self.assertEqual(alpha_perf['target'], 10)
        self.assertEqual(alpha_perf['completed'], 1)
        self.assertEqual(alpha_perf['pending'], 9)
        self.assertEqual(alpha_perf['completion_pct'], 10.0)

        # Test capping at 100%
        self.camp1.target_calls = 1
        self.camp1.save()
        perf_capped = compute_campaign_performance(campaign_id=self.camp1.id)
        self.assertLessEqual(perf_capped[0]['completion_pct'], 100.0)

    def test_telecaller_performance_metrics(self):
        """compute_telecaller_performance aggregates per-telecaller calls, duration, and followups."""
        tc_perf = compute_telecaller_performance()
        tc1_data = next((p for p in tc_perf if p['telecaller'] == self.tc1), None)
        self.assertIsNotNone(tc1_data)
        self.assertEqual(tc1_data['assigned_customers'], 2)
        self.assertEqual(tc1_data['total_calls'], 2)
        self.assertEqual(tc1_data['completed'], 1)
        self.assertEqual(tc1_data['completion_rate'], 50.0)
        self.assertEqual(tc1_data['avg_duration'], '5m 0s')
        self.assertEqual(tc1_data['followups'], 1)  # followup2 is assigned to tc1

    def test_questionnaire_analytics_aggregation(self):
        """compute_questionnaire_analytics computes options count and average ratings."""
        q_results, camp_obj = compute_questionnaire_analytics(campaign_id=self.camp1.id)
        self.assertEqual(camp_obj, self.camp1)
        self.assertEqual(len(q_results), 3)

        # Choice question
        choice_info = next(q for q in q_results if q['question'] == self.q_choice)
        self.assertEqual(choice_info['counts'].get('Email'), 1)
        self.assertEqual(choice_info['percentages'].get('Email'), 100.0)

        # Rating question
        rating_info = next(q for q in q_results if q['question'] == self.q_rating)
        self.assertEqual(rating_info['avg_rating'], 5.0)

        # Text question
        text_info = next(q for q in q_results if q['question'] == self.q_text)
        self.assertIn('Excellent service and quick support', text_info['text_responses'])

    def test_customer_response_insights(self):
        """compute_customer_response_insights extracts top responses and rating insights."""
        insights = compute_customer_response_insights(campaign_id=self.camp1.id)
        self.assertTrue(len(insights) >= 2)
        top_opt = next((i for i in insights if i['label'] == 'Most Selected Response'), None)
        self.assertIsNotNone(top_opt)
        self.assertIn('Email', top_opt['value'])

    def test_followup_analytics_breakdown(self):
        """compute_followup_analytics counts pending, overdue, and provides breakdowns."""
        fu_data = compute_followup_analytics()
        self.assertEqual(fu_data['total'], 2)
        self.assertEqual(fu_data['pending'], 1)
        self.assertEqual(fu_data['overdue'], 1)
        self.assertTrue(len(fu_data['by_campaign']) >= 1)
        self.assertTrue(len(fu_data['by_telecaller']) >= 1)

    def test_reports_view_and_preview(self):
        """Reports page renders and builds previews for all 5 report types."""
        self.client.login(username='admin_adv', password='password123')
        report_types = ['campaign', 'calls', 'telecaller', 'responses', 'followups']
        for r_type in report_types:
            response = self.client.get(reverse('reports'), {'report_type': r_type})
            self.assertEqual(response.status_code, 200)
            preview = response.context['preview']
            self.assertIsNotNone(preview, f"Preview should not be None for {r_type}")
            self.assertGreaterEqual(preview['record_count'], 0)

    def test_export_pdf_reports(self):
        """export_pdf generates valid PDF binary streams for all report types."""
        self.client.login(username='admin_adv', password='password123')
        report_types = ['campaign', 'calls', 'telecaller', 'responses', 'followups']
        for r_type in report_types:
            response = self.client.get(reverse('export_pdf'), {'report_type': r_type})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'application/pdf')
            self.assertTrue(response.content.startswith(b'%PDF'), f"Invalid PDF header for {r_type}")

    def test_export_excel_reports(self):
        """export_excel generates valid spreadsheet streams for all report types."""
        self.client.login(username='admin_adv', password='password123')
        report_types = ['campaign', 'calls', 'telecaller', 'responses', 'followups']
        for r_type in report_types:
            response = self.client.get(reverse('export_excel'), {'report_type': r_type})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            self.assertIn('attachment;', response['Content-Disposition'])

    def test_empty_states_zero_division_safety(self):
        """Analytics engine safely handles zero calls, zero campaigns, and empty datasets."""
        empty_calls = CallRecord.objects.none()
        kpis = compute_call_kpis(empty_calls)
        self.assertEqual(kpis['total_calls'], 0)
        self.assertEqual(kpis['completion_rate'], 0)
        self.assertEqual(kpis['avg_duration_sec'], 0)

        counts, total = compute_call_outcome_counts(empty_calls)
        self.assertEqual(total, 0)
        self.assertEqual(counts['Completed']['pct'], 0)

        perf = compute_campaign_performance(campaign_id=999999)
        self.assertEqual(perf, [])

        q_res, camp = compute_questionnaire_analytics(campaign_id=999999)
        self.assertEqual(q_res, [])
        self.assertIsNone(camp)
