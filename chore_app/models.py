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
    name = models.CharField(max_length=255)
    comment = models.CharField(max_length=255, default="", blank=True)
    points = models.IntegerField(default=0)
    multiplier_type = models.BooleanField(default=False)
    available = models.BooleanField(default=True)
    daily = models.BooleanField(default=False)
    persistent = models.BooleanField(default=False)
    earlyBonus = models.BooleanField(default=False)
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