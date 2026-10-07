from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from accounts.faq_data import (
    ADMIN_FAQ_CATEGORIES,
    TELECALLER_FAQ_CATEGORIES,
    GENERAL_FAQ_CATEGORY,
    get_faqs_for_user
)
from campaigns.models import Campaign
from customers.models import Customer, CampaignCustomer


class HelpCenterTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin_faq_test',
            password='password123',
            role='ADMIN',
            is_active=True
        )
        self.telecaller = User.objects.create_user(
            username='telecaller_faq_test',
            password='password123',
            role='TELE_CALLER',
            is_active=True
        )

    def test_anonymous_user_redirected_to_login(self):
        """Anonymous unauthenticated user cannot access /help/ and is redirected to login."""
        response = self.client.get(reverse('help_center'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_authenticated_admin_access_help_center(self):
        """Authenticated Admin can access Help Center with status 200."""
        self.client.login(username='admin_faq_test', password='password123')
        response = self.client.get(reverse('help_center'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'help/center.html')
        self.assertEqual(response.context['user_role_label'], 'Administrator')

    def test_authenticated_telecaller_access_help_center(self):
        """Authenticated Tele-caller can access Help Center with status 200."""
        self.client.login(username='telecaller_faq_test', password='password123')
        response = self.client.get(reverse('help_center'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'help/center.html')
        self.assertEqual(response.context['user_role_label'], 'Tele-caller')

    def test_admin_receives_admin_faq_content(self):
        """Admin receives all required Admin FAQ categories and questions."""
        self.client.login(username='admin_faq_test', password='password123')
        response = self.client.get(reverse('help_center'))
        self.assertEqual(response.status_code, 200)

        categories = response.context['faq_categories']
        cat_ids = [c['id'] for c in categories]

        # Verify all 7 Admin categories + General
        expected_admin_cats = [
            'getting-started',
            'campaign-management',
            'customer-management',
            'questionnaire-management',
            'analytics-reports',
            'telecaller-management',
            'notifications',
            'general-ccm'
        ]
        for cat_id in expected_admin_cats:
            self.assertIn(cat_id, cat_ids, f"Admin missing category: {cat_id}")

        # Check key admin questions
        self.assertContains(response, "What is CCM?")
        self.assertContains(response, "How do I create a campaign?")
        self.assertContains(response, "How do I shift a customer from one tele-caller to another?")
        self.assertContains(response, "Why are already-assigned customers not shown in the normal assignment list?")
        self.assertContains(response, "What question types are supported?")
        self.assertContains(response, "How do I generate/export reports?")

    def test_telecaller_receives_telecaller_faq_content(self):
        """Tele-caller receives all required Tele-caller FAQ categories and questions."""
        self.client.login(username='telecaller_faq_test', password='password123')
        response = self.client.get(reverse('help_center'))
        self.assertEqual(response.status_code, 200)

        categories = response.context['faq_categories']
        cat_ids = [c['id'] for c in categories]

        # Verify all 7 Tele-caller categories + General
        expected_telecaller_cats = [
            'getting-started',
            'customer-campaigns',
            'call-console',
            'questionnaire',
            'follow-ups',
            'call-history',
            'notifications',
            'general-ccm'
        ]
        for cat_id in expected_telecaller_cats:
            self.assertIn(cat_id, cat_ids, f"Tele-caller missing category: {cat_id}")

        # Check key tele-caller questions
        self.assertContains(response, "What can I do as a tele-caller?")
        self.assertContains(response, "How do I start a customer call?")
        self.assertContains(response, "How does the call stopwatch work?")
        self.assertContains(response, "Where can I find the campaign questionnaire?")
        self.assertContains(response, "How do I handle an overdue follow-up?")
        self.assertContains(response, "Can I see calls made by other tele-callers?")

    def test_strict_role_isolation_telecaller_cannot_access_admin_faqs(self):
        """Server-side strict role isolation: Tele-caller context must NEVER contain Admin operational categories."""
        self.client.login(username='telecaller_faq_test', password='password123')
        response = self.client.get(reverse('help_center'))

        categories = response.context['faq_categories']
        cat_ids = [c['id'] for c in categories]

        # Admin-only category IDs must NOT be present
        admin_only_cat_ids = [
            'campaign-management',
            'customer-management',
            'questionnaire-management',
            'analytics-reports',
            'telecaller-management'
        ]
        for cat_id in admin_only_cat_ids:
            self.assertNotIn(cat_id, cat_ids, f"Tele-caller unlawfully received Admin category: {cat_id}")

        # Admin operational questions must NOT be rendered in Tele-caller response
        self.assertNotContains(response, "How do I create a campaign?")
        self.assertNotContains(response, "How do I upload/import customers?")
        self.assertNotContains(response, "How do I shift a customer from one tele-caller to another?")
        self.assertNotContains(response, "How do I manage tele-callers?")
        self.assertNotContains(response, "How do I generate/export reports?")

    def test_admin_does_not_receive_telecaller_specific_category_ids(self):
        """Admin does not receive Tele-caller-only category IDs in their context."""
        self.client.login(username='admin_faq_test', password='password123')
        response = self.client.get(reverse('help_center'))

        categories = response.context['faq_categories']
        cat_ids = [c['id'] for c in categories]

        telecaller_only_cat_ids = [
            'customer-campaigns',
            'call-console',
            'call-history'
        ]
        for cat_id in telecaller_only_cat_ids:
            self.assertNotIn(cat_id, cat_ids, f"Admin received tele-caller-only category: {cat_id}")

    def test_general_category_visible_to_both(self):
        """General FAQ category is shared and visible to both Admin and Tele-caller."""
        # Check Admin
        self.client.login(username='admin_faq_test', password='password123')
        res_admin = self.client.get(reverse('help_center'))
        self.assertContains(res_admin, "How do I switch between Dark and Light mode?")
        self.assertContains(res_admin, "General CCM Platform")

        # Check Tele-caller
        self.client.login(username='telecaller_faq_test', password='password123')
        res_tele = self.client.get(reverse('help_center'))
        self.assertContains(res_tele, "How do I switch between Dark and Light mode?")
        self.assertContains(res_tele, "General CCM Platform")

    def test_faq_data_helper_unit_tests(self):
        """Direct unit testing of get_faqs_for_user helper function."""
        # Unauthenticated / None
        self.assertEqual(get_faqs_for_user(None), [])

        class MockAnonymousUser:
            is_authenticated = False

        self.assertEqual(get_faqs_for_user(MockAnonymousUser()), [])

        # Admin user
        admin_faqs = get_faqs_for_user(self.admin)
        self.assertEqual(len(admin_faqs), len(ADMIN_FAQ_CATEGORIES) + 1)
        self.assertEqual(admin_faqs[-1]['id'], 'general-ccm')

        # Tele-caller user
        tele_faqs = get_faqs_for_user(self.telecaller)
        self.assertEqual(len(tele_faqs), len(TELECALLER_FAQ_CATEGORIES) + 1)
        self.assertEqual(tele_faqs[-1]['id'], 'general-ccm')

    def test_search_and_accordion_attributes_present(self):
        """Verify the template renders search inputs, empty-state containers, and data attributes for client search."""
        self.client.login(username='admin_faq_test', password='password123')
        response = self.client.get(reverse('help_center'))

        self.assertContains(response, 'id="faqSearchInput"')
        self.assertContains(response, 'id="noResultsState"')
        self.assertContains(response, 'No matching FAQs found')
        self.assertContains(response, 'data-question=')
        self.assertContains(response, 'data-answer=')
        self.assertContains(response, 'aria-expanded=')
        self.assertContains(response, 'expandAllBtn')
        self.assertContains(response, 'collapseAllBtn')

    def test_navbar_contains_help_button(self):
        """Navbar contains the Help & FAQ button linking to /help/."""
        self.client.login(username='admin_faq_test', password='password123')
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'id="helpBtn"')
        self.assertContains(response, reverse('help_center'))

    def test_contextual_help_link_on_customer_assign(self):
        """Customer assignment page contains contextual help link."""
        self.client.login(username='admin_faq_test', password='password123')
        response = self.client.get(reverse('customer_assign'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('help_center') + '#customer-management')
        self.assertContains(response, 'Need help assigning customers? View FAQ →')

    def test_contextual_help_link_on_followups(self):
        """Follow-ups page contains contextual help link."""
        self.client.login(username='telecaller_faq_test', password='password123')
        response = self.client.get(reverse('followup_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('help_center') + '#follow-ups')
        self.assertContains(response, 'Need help managing follow-ups? View FAQ →')
