from django.db import models
from django.conf import settings

class Campaign(models.Model):
    STATUS_CHOICES = (
        ('Draft', 'Draft'),
        ('Active', 'Active'),
        ('Paused', 'Paused'),
        ('Completed', 'Completed'),
        ('Archived', 'Archived'),
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    campaign_type = models.CharField(max_length=100, default='Tele-calling')
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft', db_index=True)
    target_calls = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_campaigns')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

class Questionnaire(models.Model):
    campaign = models.OneToOneField(Campaign, on_delete=models.CASCADE, related_name='questionnaire')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Questionnaire: {self.title} ({self.campaign.name})"

class Question(models.Model):
    QUESTION_TYPES = (
        ('single_choice', 'Single Choice'),
        ('multiple_choice', 'Multiple Choice'),
        ('rating_scale', 'Rating Scale (1-5)'),
        ('open_ended', 'Open Ended'),
        ('yes_no', 'Yes / No'),
    )

    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=30, choices=QUESTION_TYPES)
    options = models.JSONField(default=list, blank=True)
    required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"Q: {self.question_text[:40]} ({self.get_question_type_display()})"
