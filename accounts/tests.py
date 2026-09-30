from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from campaigns.models import Campaign
from customers.models import Customer, CampaignCustomer
from calls.models import CallRecord, FollowUp

class AccountTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin_test', password='password123', role='ADMIN'
        )
        self.telecaller = User.objects.create_user(
            username='telecaller_test', password='password123', role='TELE_CALLER'
        )

    def test_login_valid_credentials(self):
        response = self.client.post(reverse('login'), {
            'username': 'admin_test',
            'password': 'password123'
        })
        self.assertRedirects(response, reverse('dashboard'))

    def test_login_invalid_credentials(self):
        response = self.client.post(reverse('login'), {
            'username': 'admin_test',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('errors', response.context)

    def test_unauthorized_access_to_admin_sections(self):
        # Telecaller trying to access admin endpoints directly
        self.client.login(username='telecaller_test', password='password123')
        
        admin_urls = [
            reverse('telecaller_list'),
            reverse('telecaller_create'),
            reverse('campaign_create'),
            reverse('customer_create'),
            reverse('customer_import'),
            reverse('customer_assign'),
            reverse('analytics'),
            reverse('reports'),
            reverse('export_pdf'),
            reverse('export_excel'),
        ]
        
        for url in admin_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403, f"Expected HTTP 403 for {url}")

    def test_public_home_page_accessible_anonymously(self):
        """Root URL / loads the public CCM landing page without authentication."""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Centralized Customer")
        self.assertContains(response, "Sign In")
        self.assertContains(response, "Enterprise Campaign & Tele-calling Operations Platform")

    def test_public_home_page_for_authenticated_users(self):
        """Authenticated users visiting / see quick access to their dashboard."""
        self.client.login(username='admin_test', password='password123')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Open Dashboard")

    def test_role_based_dashboard_dispatch(self):
        """Admins and tele-callers both land on their respective role-aware dashboards."""
        # Admin dispatch
        self.client.login(username='admin_test', password='password123')
        resp_admin = self.client.get(reverse('dashboard'))
        self.assertEqual(resp_admin.status_code, 200)
        self.assertIn('campaign_progress_list', resp_admin.context)

        # Telecaller dispatch
        self.client.login(username='telecaller_test', password='password123')
        resp_tc = self.client.get(reverse('dashboard'))
        self.assertEqual(resp_tc.status_code, 200)
        self.assertIn('next_tasks', resp_tc.context)

    def test_logout_behavior(self):
        """POST to logout terminates session and redirects back to login page."""
        self.client.login(username='admin_test', password='password123')
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))
        # Following dashboard after logout redirects to login
        dash_resp = self.client.get(reverse('dashboard'))
        self.assertRedirects(dash_resp, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_health_check_endpoint(self):
        """Health check endpoint /health/ returns healthy status and database connection."""
        response = self.client.get(reverse('health_check'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'healthy')
        self.assertEqual(data.get('database'), 'connected')

    def test_login_page_renders_role_selection_and_back_to_home(self):
        """Login page displays 'Who are you?', role cards, and 'Back to Home' pointing to '/'."""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Who are you?")
        self.assertContains(response, "Administrator")
        self.assertContains(response, "Tele-caller")
        self.assertContains(response, "Back to Home")
        self.assertContains(response, 'href="/"')

    def test_login_page_with_role_query_parameter(self):
        """Passing ?role=ADMIN or ?role=TELE_CALLER reveals the appropriate login form and Change Role button."""
        # Admin preselection
        resp_admin = self.client.get(reverse('login') + '?role=ADMIN')
        self.assertEqual(resp_admin.status_code, 200)
        self.assertContains(resp_admin, "Administrator Login")
        self.assertContains(resp_admin, "Change Role")
        self.assertContains(resp_admin, 'value="ADMIN"')

        # Telecaller preselection
        resp_tc = self.client.get(reverse('login') + '?role=TELE_CALLER')
        self.assertEqual(resp_tc.status_code, 200)
        self.assertContains(resp_tc, "Tele-caller Login")
        self.assertContains(resp_tc, "Change Role")
        self.assertContains(resp_tc, 'value="TELE_CALLER"')

    def test_login_with_correct_role_selection(self):
        """When selected role matches user account role, login succeeds and redirects."""
        # Admin login with ADMIN selected
        resp_admin = self.client.post(reverse('login'), {
            'username': 'admin_test',
            'password': 'password123',
            'selected_role': 'ADMIN'
        })
        self.assertRedirects(resp_admin, reverse('dashboard'))

        self.client.logout()

        # Telecaller login with TELE_CALLER selected
        resp_tc = self.client.post(reverse('login'), {
            'username': 'telecaller_test',
            'password': 'password123',
            'selected_role': 'TELE_CALLER'
        })
        self.assertRedirects(resp_tc, reverse('dashboard'))

    def test_login_role_mismatch_admin_selected_for_telecaller_account(self):
        """Selecting Administrator but entering Tele-caller credentials rejects login with role mismatch error."""
        response = self.client.post(reverse('login'), {
            'username': 'telecaller_test',
            'password': 'password123',
            'selected_role': 'ADMIN'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The selected role does not match this account. Please select the correct role.")
        # Ensure user is NOT authenticated
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_role_mismatch_telecaller_selected_for_admin_account(self):
        """Selecting Tele-caller but entering Administrator credentials rejects login with role mismatch error."""
        response = self.client.post(reverse('login'), {
            'username': 'admin_test',
            'password': 'password123',
            'selected_role': 'TELE_CALLER'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The selected role does not match this account. Please select the correct role.")
        # Ensure user is NOT authenticated
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_telecaller_detail_loads_successfully_without_queryset_slicing_error(self):
        """Regression test for Bug 1: /tele-callers/<id>/ must not crash with TypeError when counting/slicing querysets."""
        self.client.login(username='admin_test', password='password123')
        
        campaign = Campaign.objects.create(
            name="Q4 Enterprise Outreach",
            campaign_type="Sales",
            status="Active",
            start_date=timezone.localtime().date(),
            end_date=timezone.localtime().date(),
            target_calls=50,
            created_by=self.admin
        )
        customer = Customer.objects.create(name="Acme Corp", phone="+15550001", company="Acme")
        CampaignCustomer.objects.create(campaign=campaign, customer=customer, assigned_telecaller=self.telecaller)

        now = timezone.now()
        CallRecord.objects.create(
            customer=customer,
            telecaller=self.telecaller,
            campaign=campaign,
            call_status='Completed',
            call_start_time=now,
            call_end_time=now,
            duration=45
        )
        CallRecord.objects.create(
            customer=customer,
            telecaller=self.telecaller,
            campaign=campaign,
            call_status='No Answer',
            call_start_time=now,
            call_end_time=now,
            duration=0
        )
        FollowUp.objects.create(
            customer=customer,
            assigned_to=self.telecaller,
            scheduled_date=timezone.localtime().date(),
            scheduled_time=timezone.localtime().time(),
            status='Pending'
        )

        response = self.client.get(reverse('telecaller_detail', args=[self.telecaller.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.telecaller.username)
        self.assertContains(response, "Recent Call Activity")
        self.assertContains(response, "Assigned Workload")
        self.assertEqual(response.context['completed_calls'], 1)
        self.assertEqual(response.context['assigned_count'], 1)

    def test_telecaller_detail_forbidden_for_telecaller(self):
        """Tele-callers must receive HTTP 403 Forbidden when attempting to view telecaller detail page."""
        self.client.login(username='telecaller_test', password='password123')
        response = self.client.get(reverse('telecaller_detail', args=[self.telecaller.pk]))
        self.assertEqual(response.status_code, 403)

    def test_home_page_explore_capabilities_and_theme_toggle_elements(self):
        """Verify Explore Capabilities button, section anchors, How It Works, and Theme Toggle on home page."""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Explore Capabilities')
        self.assertContains(response, 'href="#features"')
        self.assertContains(response, 'id="features"')
        self.assertContains(response, 'id="how-it-works"')
        self.assertContains(response, 'How CCM Works in 3 Steps')
        self.assertContains(response, 'id="themeToggleBtn"')
        self.assertContains(response, 'Manage Every')

    def test_telecaller_edit_form_does_not_contain_password_input(self):
        """Edit Tele-caller form must not expose password input fields; it must show password security guidance."""
        self.client.login(username='admin_test', password='password123')
        response = self.client.get(reverse('telecaller_edit', args=[self.telecaller.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="password"')
        self.assertContains(response, 'Password Security')
        self.assertContains(response, reverse('telecaller_reset_password', args=[self.telecaller.pk]))

    def test_telecaller_edit_updates_profile_fields(self):
        """Editing telecaller updates contact info and active status without modifying credentials."""
        self.client.login(username='admin_test', password='password123')
        response = self.client.post(reverse('telecaller_edit', args=[self.telecaller.pk]), {
            'first_name': 'UpdatedFirst',
            'last_name': 'UpdatedLast',
            'email': 'updated@example.com',
            'phone': '+1999888777',
            'is_active': 'on'
        })
        self.assertRedirects(response, reverse('telecaller_detail', args=[self.telecaller.pk]))
        self.telecaller.refresh_from_db()
        self.assertEqual(self.telecaller.first_name, 'UpdatedFirst')
        self.assertEqual(self.telecaller.email, 'updated@example.com')
        # Check original password still works
        self.assertTrue(self.telecaller.check_password('password123'))

    def test_telecaller_reset_password_forbidden_for_telecaller(self):
        """Non-admin users cannot initiate password resets for telecallers (HTTP 403)."""
        self.client.login(username='telecaller_test', password='password123')
        response = self.client.get(reverse('telecaller_reset_password', args=[self.telecaller.pk]))
        self.assertEqual(response.status_code, 403)

    def test_telecaller_reset_password_workflow_and_confirmation(self):
        """Admin can trigger password reset; user uses token to reset password and login with new password."""
        self.telecaller.email = 'telecaller@example.com'
        self.telecaller.save()

        self.client.login(username='admin_test', password='password123')
        # GET confirmation page
        resp_get = self.client.get(reverse('telecaller_reset_password', args=[self.telecaller.pk]))
        self.assertEqual(resp_get.status_code, 200)
        self.assertContains(resp_get, "Reset Tele-caller Password")

        # POST dispatches reset link
        resp_post = self.client.post(reverse('telecaller_reset_password', args=[self.telecaller.pk]))
        self.assertRedirects(resp_post, reverse('telecaller_detail', args=[self.telecaller.pk]))

        # Generate token and test user reset confirmation
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        token = default_token_generator.make_token(self.telecaller)
        uidb64 = urlsafe_base64_encode(force_bytes(self.telecaller.pk))
        reset_confirm_url = reverse('password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})

        # Logout admin and visit reset confirm page as anonymous user
        self.client.logout()
        resp_confirm_get = self.client.get(reset_confirm_url)
        self.assertEqual(resp_confirm_get.status_code, 200)
        self.assertContains(resp_confirm_get, "Set New Password")

        # Submit new password
        resp_confirm_post = self.client.post(reset_confirm_url, {
            'new_password': 'BrandNewPassword456!',
            'confirm_password': 'BrandNewPassword456!',
        })
        self.assertRedirects(resp_confirm_post, reverse('login'))

        # Verify old password fails and new password succeeds
        self.telecaller.refresh_from_db()
        self.assertFalse(self.telecaller.check_password('password123'))
        self.assertTrue(self.telecaller.check_password('BrandNewPassword456!'))

    def test_deactivated_account_cannot_login_and_cannot_reset_password(self):
        """Deactivated user account is denied login and cannot have password reset."""
        self.telecaller.is_active = False
        self.telecaller.email = 'inactive@example.com'
        self.telecaller.save()

        # Login fails with account deactivated message
        resp_login = self.client.post(reverse('login'), {
            'username': 'telecaller_test',
            'password': 'password123',
            'selected_role': 'TELE_CALLER'
        })
        self.assertEqual(resp_login.status_code, 200)
        self.assertContains(resp_login, "Your account has been deactivated.")

        # Admin reset password check blocks deactivated account
        self.client.login(username='admin_test', password='password123')
        resp_reset = self.client.post(reverse('telecaller_reset_password', args=[self.telecaller.pk]))
        self.assertRedirects(resp_reset, reverse('telecaller_detail', args=[self.telecaller.pk]))


