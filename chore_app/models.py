from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal


class User(AbstractUser):
    role = models.CharField(max_length=10, choices=(
        ('Parent', 'Parent'), ('Child', 'Child')), db_index=True)
    points_balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    pocket_money = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    place_1 = models.IntegerField(default=0)
    place_2 = models.IntegerField(default=0)
    place_3 = models.IntegerField(default=0)


class Chore(models.Model):
    ASSIGNMENT_CHOICES = [
        ('any_child', 'Any Child'),
        ('all_children', 'All Children'),
        ('any_selected', 'Any of Selected Children'),
        ('all_selected', 'All of Selected Children'),
    ]
    
    name = models.CharField(max_length=255)
    comment = models.CharField(max_length=255, default="", blank=True)
    points = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    multiplier_type = models.BooleanField(default=False)
    available = models.BooleanField(default=True, db_index=True)
    daily = models.BooleanField(default=False)
    assignment_type = models.CharField(max_length=20, choices=ASSIGNMENT_CHOICES, default='any_child')
    assigned_children = models.ManyToManyField('User', blank=True, related_name='assigned_chores', limit_choices_to={'role': 'Child'})
    early_bonus = models.BooleanField(default=False)
    bonus_end_time = models.IntegerField(default=14, help_text="Hour when bonus expires (24-hour format, 0-23)")
    available_time = models.IntegerField(default=0)
    
    def clean(self):
        super().clean()
        if not (0 <= self.bonus_end_time <= 23):
            raise ValidationError({'bonus_end_time': 'Bonus end time must be between 0 and 23 (24-hour format)'})
    
    class Meta:
        indexes = [
            models.Index(fields=['assignment_type', 'available']),  # For filtering by assignment type and availability
            models.Index(fields=['available', 'available_time']),    # For time-based filtering
        ]


class ChoreClaim(models.Model):
    chore = models.ForeignKey(Chore, on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    chore_name = models.CharField(max_length=255, default="", db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_choreclaim', db_index=True)
    approved = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), db_index=True)
    points = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    multiplier_type = models.BooleanField(default=False)
    comment = models.CharField(max_length=255, default="", blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'approved']),
            models.Index(fields=['chore', 'user']),
            models.Index(fields=['chore', 'user', 'approved']),  # For filtering claimed chores by other users
        ]


class PointLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    points_change = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    reason = models.CharField(max_length=255, blank=True)
    chore = models.CharField(max_length=255, db_index=True)
    penalty = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    multiplier_type = models.BooleanField(default=False)
    date_recorded = models.DateTimeField(auto_now_add=True, db_index=True)
    approver = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='approver_pointlogs')
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'date_recorded']),
            models.Index(fields=['date_recorded']),
            models.Index(fields=['chore', 'date_recorded']),
        ]


class Settings(models.Model):
    key = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255, default="")
    value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

class Text(models.Model):
    key = models.CharField(max_length=255, unique=True)
    text = models.TextField(default="")
    enabled = models.BooleanField(default=True)

class RunLog(models.Model):
    job_code = models.CharField(max_length=255)
    run_date = models.DateField()
    
    class Meta:
        unique_together = ('job_code', 'run_date')