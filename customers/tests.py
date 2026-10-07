import io
import openpyxl
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from accounts.models import User
from customers.models import Customer, CampaignCustomer
from campaigns.models import Campaign
from calls.models import CallRecord, FollowUp


class CustomerTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username='admin_cust', password='password123', role='ADMIN')
        self.telecaller = User.objects.create_user(username='tc_cust', password='password123', role='TELE_CALLER')
        self.client.login(username='admin_cust', password='password123')

        self.campaign = Campaign.objects.create(
            name='Customer Test Campaign',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            status='Active',
            created_by=self.admin
        )

    def test_customer_creation(self):
        response = self.client.post(reverse('customer_create'), {
            'name': 'John Doe Lead',
            'phone': '+15559900',
            'email': 'john@lead.com',
            'company': 'Lead Co'
        })
        self.assertTrue(Customer.objects.filter(phone='+15559900').exists())

    def test_customer_creation_with_whatsapp_and_notes(self):
        response = self.client.post(reverse('customer_create'), {
            'name': 'WhatsApp VIP Lead',
            'phone': '+15551234567',
            'whatsapp_number': '+15559876543',
            'email': 'wa_vip@lead.com',
            'company': 'VIP Enterprise',
            'notes': 'High priority account with WhatsApp preference'
        })
        cust = Customer.objects.filter(phone='+15551234567').first()
        self.assertIsNotNone(cust)
        self.assertEqual(cust.whatsapp_number, '+15559876543')
        self.assertEqual(cust.notes, 'High priority account with WhatsApp preference')
        self.assertTrue(cust.is_active)

    def test_customer_creation_without_whatsapp(self):
        response = self.client.post(reverse('customer_create'), {
            'name': 'No WhatsApp Lead',
            'phone': '+15557766554',
            'email': 'nowa@lead.com',
            'company': 'Standard Co',
            'whatsapp_number': ''
        })
        cust = Customer.objects.filter(phone='+15557766554').first()
        self.assertIsNotNone(cust)
        self.assertIsNone(cust.whatsapp_number)

    def test_customer_invalid_whatsapp_rejection(self):
        response = self.client.post(reverse('customer_create'), {
            'name': 'Bad WA Lead',
            'phone': '+15559988771',
            'whatsapp_number': '123'  # Too short, fails minimum 7 digits check
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Customer.objects.filter(phone='+15559988771').exists())
        self.assertIn('whatsapp_number', response.context.get('errors', {}))

    def test_customer_edit(self):
        cust = Customer.objects.create(name='Original Name', phone='+15554433221')
        response = self.client.post(reverse('customer_edit', kwargs={'pk': cust.pk}), {
            'name': 'Updated Name',
            'phone': '+15554433221',
            'whatsapp_number': '+15553322110',
            'email': 'updated@lead.com',
            'company': 'New Corp',
            'address': '123 Street',
            'city': 'Metropolis',
            'state': 'NY',
            'notes': 'Updated profile notes',
            # is_active not passed -> uncheck sets False
        })
        cust.refresh_from_db()
        self.assertEqual(cust.name, 'Updated Name')
        self.assertEqual(cust.whatsapp_number, '+15553322110')
        self.assertEqual(cust.notes, 'Updated profile notes')
        self.assertFalse(cust.is_active)

    def test_customer_delete_soft_delete_preserves_history(self):
        cust = Customer.objects.create(name='Lead With History', phone='+15550011223')
        call_rec = CallRecord.objects.create(
            campaign=self.campaign,
            customer=cust,
            telecaller=self.telecaller,
            call_status='Completed',
            call_start_time=timezone.now(),
            duration=60
        )
        response = self.client.post(reverse('customer_delete', kwargs={'pk': cust.pk}))
        # Customer should NOT be purged from DB; should be deactivated (archived)
        cust.refresh_from_db()
        self.assertFalse(cust.is_active)
        self.assertTrue(Customer.objects.filter(pk=cust.pk).exists())
        self.assertTrue(CallRecord.objects.filter(pk=call_rec.pk).exists())

    def test_customer_delete_hard_delete_without_history(self):
        cust = Customer.objects.create(name='No History Lead', phone='+15559900112')
        cust_id = cust.pk
        response = self.client.post(reverse('customer_delete', kwargs={'pk': cust.pk}))
        # Customer has zero calls, followups, or campaign links -> permanent delete
        self.assertFalse(Customer.objects.filter(pk=cust_id).exists())

    def test_customer_restore(self):
        cust = Customer.objects.create(name='Archived Lead', phone='+15558877665', is_active=False)
        response = self.client.post(reverse('customer_restore', kwargs={'pk': cust.pk}))
        cust.refresh_from_db()
        self.assertTrue(cust.is_active)

    def test_customer_assignment(self):
        cust = Customer.objects.create(name='Jane Lead', phone='+15559911')
        response = self.client.post(reverse('customer_assign'), {
            'campaign_id': self.campaign.id,
            'telecaller_id': self.telecaller.id,
            'customer_ids': [cust.id]
        })
        self.assertTrue(CampaignCustomer.objects.filter(customer=cust, assigned_telecaller=self.telecaller).exists())

    def test_inactive_customer_excluded_from_assignment(self):
        active_cust = Customer.objects.create(name='Active Lead', phone='+15551111000', is_active=True)
        inactive_cust = Customer.objects.create(name='Inactive Lead', phone='+15552222000', is_active=False)

        # GET assign page should not include inactive customer
        get_res = self.client.get(reverse('customer_assign'))
        customers_in_context = list(get_res.context['customers'])
        self.assertIn(active_cust, customers_in_context)
        self.assertNotIn(inactive_cust, customers_in_context)

        # POST assign should skip inactive customer
        post_res = self.client.post(reverse('customer_assign'), {
            'campaign_id': self.campaign.id,
            'telecaller_id': self.telecaller.id,
            'customer_ids': [inactive_cust.id]
        })
        self.assertFalse(CampaignCustomer.objects.filter(customer=inactive_cust).exists())

    def test_customer_csv_import_with_whatsapp_and_notes(self):
        csv_content = (
            "name,phone,whatsapp_number,email,company,address,city,state,notes\n"
            "CSV Lead,+15553334444,+15559990000,csv@test.com,CSV Corp,100 Main,New York,NY,Imported CSV VIP Note\n"
        )
        csv_file = SimpleUploadedFile("test_leads.csv", csv_content.encode('utf-8'), content_type="text/csv")

        # Step 1: Upload preview
        upload_res = self.client.post(reverse('customer_import'), {'upload_file': csv_file})
        self.assertEqual(upload_res.status_code, 200)
        self.assertIn('import_rows', self.client.session)

        # Step 2: Confirm import
        confirm_res = self.client.post(reverse('customer_import'), {'confirm_import': '1'})
        self.assertRedirects(confirm_res, reverse('customer_list'))

        imported_cust = Customer.objects.filter(phone='+15553334444').first()
        self.assertIsNotNone(imported_cust)
        self.assertEqual(imported_cust.name, 'CSV Lead')
        self.assertEqual(imported_cust.whatsapp_number, '+15559990000')
        self.assertEqual(imported_cust.notes, 'Imported CSV VIP Note')
        self.assertTrue(imported_cust.is_active)

    def test_customer_xlsx_import_with_whatsapp_and_notes(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['name', 'phone', 'whatsapp_number', 'email', 'company', 'address', 'city', 'state', 'notes'])
        ws.append(['XLSX Lead', '+15557778888', '+15556665555', 'xlsx@test.com', 'Excel Inc', '200 Park', 'Boston', 'MA', 'Excel imported notes'])

        xlsx_io = io.BytesIO()
        wb.save(xlsx_io)
        xlsx_io.seek(0)

        xlsx_file = SimpleUploadedFile(
            "test_leads.xlsx",
            xlsx_io.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        upload_res = self.client.post(reverse('customer_import'), {'upload_file': xlsx_file})
        self.assertEqual(upload_res.status_code, 200)
        self.assertIn('import_rows', self.client.session)

        confirm_res = self.client.post(reverse('customer_import'), {'confirm_import': '1'})
        self.assertRedirects(confirm_res, reverse('customer_list'))

        imported_cust = Customer.objects.filter(phone='+15557778888').first()
        self.assertIsNotNone(imported_cust)
        self.assertEqual(imported_cust.name, 'XLSX Lead')
        self.assertEqual(imported_cust.whatsapp_number, '+15556665555')
        self.assertEqual(imported_cust.notes, 'Excel imported notes')
        self.assertTrue(imported_cust.is_active)

    def test_customer_list_activity_filter(self):
        active_cust = Customer.objects.create(name='Active Filtering Lead', phone='+15558880001', is_active=True)
        archived_cust = Customer.objects.create(name='Archived Filtering Lead', phone='+15558880002', is_active=False)

        res_active = self.client.get(reverse('customer_list') + '?activity=active')
        customers_active = [d['customer'] for d in res_active.context['customers_data']]
        self.assertIn(active_cust, customers_active)
        self.assertNotIn(archived_cust, customers_active)

        res_archived = self.client.get(reverse('customer_list') + '?activity=archived')
        customers_archived = [d['customer'] for d in res_archived.context['customers_data']]
        self.assertIn(archived_cust, customers_archived)
        self.assertNotIn(active_cust, customers_archived)
