from django import forms

from chore_app.models import Chore, ChoreClaim, PointLog, Settings, User, Text


class ChoreForm(forms.ModelForm):
    class Meta:
        model = Chore
        fields = ['name', 'comment', 'points', 'available',
                  'daily', 'assignment_type', 'assigned_children', 'early_bonus', 'bonus_end_time', 'available_time']
        labels = {
            'name': 'Chore Name',
            'comment': 'Details of Chore',
            'points': 'Points',
            'available': 'Is Available',
            'daily': 'Automatically Available Daily',
            'assignment_type': 'Assignment Type',
            'assigned_children': 'Select Children (for "Any of Selected" or "All of Selected")',
            'early_bonus': 'Early Bonus Points if done early',
            'bonus_end_time': 'Bonus Points Before (hour, 0-23)',
            'available_time': 'Time in which chore is available (+13 means after 1pm, -13 means before 1pm)'
        }
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional'}),
            'available_time': forms.NumberInput(attrs={'type': 'number', 'step': 'any'}),
            'bonus_end_time': forms.NumberInput(attrs={'type': 'number', 'min': '0', 'max': '23'}),
            'assigned_children': forms.CheckboxSelectMultiple()
        }


class EditChoreForm(forms.ModelForm):
    class Meta:
        model = Chore
        fields = ['name', 'comment', 'points', 'available',
                  'daily', 'assignment_type', 'assigned_children', 'early_bonus', 'bonus_end_time', 'available_time']
        labels = {
            'name': 'Chore Name',
            'comment': 'Details of Chore',
            'points': 'Points',
            'available': 'Is Available',
            'daily': 'Automatically Available Daily',
            'assignment_type': 'Assignment Type',
            'assigned_children': 'Select Children (for "Any of Selected" or "All of Selected")',
            'early_bonus': 'Early Bonus Points if done early',
            'bonus_end_time': 'Bonus Points Before (hour, 0-23)',
            'available_time': 'Time in which chore is available (+ for after, - for before, 0 for always available)'
        }
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional'}),
            'available_time': forms.NumberInput(attrs={'type': 'number', 'step': 'any'}),
            'bonus_end_time': forms.NumberInput(attrs={'type': 'number', 'min': '0', 'max': '23'}),
            'assigned_children': forms.CheckboxSelectMultiple()
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
        fields = ['chore_name', 'points', 'comment']
        labels = {
            'chore_name': 'What did you do?',
            'points': 'How many points is it worth?',
            'comment': 'Any additional comments?'
        }
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional'}),
            'points': forms.NumberInput(attrs={'type': 'number', 'step': 'any'})
        }


class EditSettingsForm(forms.ModelForm):
    class Meta:
        model = Settings
        fields = ['key', 'name', 'value']
        labels = {
            'key': 'Key',
            'name': 'Name of Setting',
            'value': 'Value of Setting'
        }
        widgets = {
            'key': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

class EditTextForm(forms.ModelForm):
    class Meta:
        model = Text
        fields = ['key', 'text', 'enabled']
        labels = {
            'key': 'Key',
            'text': 'Text'
        }
        widgets = {
            'key': forms.TextInput(attrs={'readonly': 'readonly'}),
        }