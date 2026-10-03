from django.db import models
from django.conf import settings
from campaigns.models import Campaign, Question
from customers.models import Customer

class CallRecord(models.Model):
    CALL_STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('No Answer', 'No Answer'),
        ('Unreachable', 'Unreachable'),
        ('Busy', 'Busy'),
        ('Follow-up Required', 'Follow-up Required'),
    )

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='call_records')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='call_records')
    telecaller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='call_records')
    call_status = models.CharField(max_length=30, choices=CALL_STATUS_CHOICES, db_index=True)
    call_start_time = models.DateTimeField()
    call_end_time = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(default=0)  # Seconds
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(duration__gte=0),
                name='call_duration_non_negative'
            ),
        ]

    def __str__(self):
        return f"Call to {self.customer.name} - Status: {self.call_status}"

class QuestionResponse(models.Model):
    call_record = models.ForeignKey(CallRecord, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='responses')
    response_text = models.TextField(blank=True)
    selected_options = models.JSONField(default=list, blank=True)
    rating = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['call_record', 'question'],
                name='unique_response_per_question'
            ),
        ]

    def __str__(self):
        return f"Response to Q{self.question.id} for Call #{self.call_record.id}"

class FollowUp(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Overdue', 'Overdue'),
        ('Cancelled', 'Cancelled'),
    )

    call_record = models.ForeignKey(CallRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name='follow_ups')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='follow_ups')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='follow_ups')
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending', db_index=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_date', 'scheduled_time']

    def __str__(self):
        return f"FollowUp with {self.customer.name} on {self.scheduled_date} ({self.status})"
