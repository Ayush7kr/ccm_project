from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from customers.models import Customer, CampaignCustomer
from campaigns.models import Campaign
from datetime import date, timedelta

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

    def test_customer_assignment(self):
        cust = Customer.objects.create(name='Jane Lead', phone='+15559911')
        response = self.client.post(reverse('customer_assign'), {
            'campaign_id': self.campaign.id,
            'telecaller_id': self.telecaller.id,
            'customer_ids': [cust.id]
        })
        self.assertTrue(CampaignCustomer.objects.filter(customer=cust, assigned_telecaller=self.telecaller).exists())
