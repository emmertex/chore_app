from chore_app.models import Chore, User, PointLog, ChoreClaim, Settings
from django import forms

class ChoreForm(forms.ModelForm):
    class Meta:
        model = Chore
        fields = ['name', 'comment', 'points', 'available', 'daily', 'persistent', 'earlyBonus', 'availableTime']
        labels = {
            'name': 'Chore Name',
            'comment': 'Details of Chore',
            'points': 'Points',
            'available': 'Is Available',
            'daily': 'Automatically Available Daily',
            'persistent': 'Available for All Children',
            'earlyBonus': 'Early Bonus Points if done early',
            'availableTime': 'Time in which chore is available (+13 means after 1pm, -13 means before 1pm)' 
        }

class EditChoreForm(forms.ModelForm):
    class Meta:
        model = Chore
        fields = ['name', 'comment', 'points', 'available', 'daily', 'persistent', 'earlyBonus', 'availableTime']
        labels = {
            'name': 'Chore Name',
            'comment': 'Details of Chore',
            'points': 'Points',
            'available': 'Is Available',
            'daily': 'Automatically Available Daily',
            'persistent': 'Available for All Children',
            'earlyBonus': 'Early Bonus Points if done early',
            'availableTime': 'Time in which chore is available (+ for after, - for before, 0 for always available)' 
        }

class PointAdjustmentForm(forms.ModelForm):
    class Meta:
        model = PointLog
        fields = ['points_change', 'reason']
        labels = {
            'points_change': 'Points Change',
            'reason': 'Reason for the Adjustment'
        }
        widgets = {
            'points_change': forms.NumberInput(attrs={'type': 'number', 'step': 'any'})
        }

class PocketMoneyAdjustmentForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['pocket_money']
        labels = {
            'pocket_money': 'Adjust Pocket Money'
        }
        widgets = {
            'pocket_money': forms.NumberInput(attrs={'type': 'number', 'step': 'any'})
        }

class CustomChildChore(forms.ModelForm):
    class Meta:
        model = ChoreClaim
        fields = ['choreName', 'points', 'comment']
        labels = {
            'choreName': 'What did you do?',
            'points': 'How many points is it worth?',
            'comment': 'Any additional comments?'
        }
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional'}),
            'points': forms.NumberInput(attrs={'type': 'number', 'step': 'any'})
        }
