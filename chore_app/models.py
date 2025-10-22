from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    role = models.CharField(max_length=10, choices=(
        ('Parent', 'Parent'), ('Child', 'Child')))
    points_balance = models.IntegerField(default=0)
    pocket_money = models.IntegerField(default=0)
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
    points = models.IntegerField(default=0)
    multiplier_type = models.BooleanField(default=False)
    available = models.BooleanField(default=True)
    daily = models.BooleanField(default=False)
    assignment_type = models.CharField(max_length=20, choices=ASSIGNMENT_CHOICES, default='any_child')
    assigned_children = models.ManyToManyField('User', blank=True, related_name='assigned_chores', limit_choices_to={'role': 'Child'})
    earlyBonus = models.BooleanField(default=False)
    bonus_end_time = models.IntegerField(default=14, help_text="Hour when bonus expires (24-hour format, 0-23)")
    availableTime = models.IntegerField(default=0)


class ChoreClaim(models.Model):
    chore = models.ForeignKey(Chore, on_delete=models.CASCADE, blank=True, null=True, default=None)
    choreName = models.CharField(max_length=255, default="")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_choreclaim')
    approved = models.IntegerField(default=0)
    points = models.IntegerField(default=0)
    multiplier_type = models.BooleanField(default=False)
    comment = models.CharField(max_length=255, default="", blank=True)


class PointLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    points_change = models.IntegerField(default=0)
    reason = models.CharField(max_length=255, blank=True)
    chore = models.CharField(max_length=255)
    penalty = models.IntegerField(default=0)
    multiplier_type = models.BooleanField(default=False)
    date_recorded = models.DateTimeField(auto_now_add=True)
    approver = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='approver_pointlogs')


class Settings(models.Model):
    key = models.CharField(max_length=255)
    name = models.CharField(max_length=255, default="")
    value = models.IntegerField(default=0)

class Text(models.Model):
    key = models.CharField(max_length=255)
    text = models.TextField(default="")
    enabled = models.BooleanField(default=True)

class RunLog(models.Model):
    job_code = models.CharField(max_length=255)
    run_date = models.DateField()