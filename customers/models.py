from django.db import models
from django.conf import settings
from campaigns.models import Campaign

class Customer(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, db_index=True)
    email = models.EmailField(blank=True, null=True)
    company = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    source = models.CharField(max_length=100, default='Direct Input')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.phone})"

class CampaignCustomer(models.Model):
    STATUS_CHOICES = (
        ('Unassigned', 'Unassigned'),
        ('Assigned', 'Assigned'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    )

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='customer_assignments')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='campaign_links')
    assigned_telecaller = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_customers'
    )
    assignment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Unassigned', db_index=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('campaign', 'customer')
        ordering = ['-created_at']

    def __str__(self):
        caller = self.assigned_telecaller.get_full_name() if self.assigned_telecaller else 'Unassigned'
        return f"{self.customer.name} - {self.campaign.name} ({caller})"
