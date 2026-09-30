from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Administrator'),
        ('TELE_CALLER', 'Tele-caller'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='TELE_CALLER', db_index=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_admin_user(self):
        return self.role == 'ADMIN'

    @property
    def is_telecaller_user(self):
        return self.role == 'TELE_CALLER'

    def __str__(self):
        full_name = self.get_full_name()
        return f"{full_name} ({self.username})" if full_name else self.username
