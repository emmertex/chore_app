from django import forms

from chore_app.models import Chore, ChoreClaim, PointLog, Reward, Text


class ChoreForm(forms.ModelForm):
    """Create a chore. `assignment_type` decides whether assigned_children applies."""

    assignment_type = forms.ChoiceField(
        choices=[
            ('any', 'Any Child'),
            ('specific', 'Specific Children Only'),
        ],
        widget=forms.RadioSelect,
        label='Who can claim this chore?',
        initial='any'
    )

    class Meta:
        model = Chore
        fields = ['name', 'comment', 'points', 'available',
                  'daily', 'assigned_children', 'early_bonus', 'bonus_end_time']
        labels = {
            'name': 'Chore Name',
            'comment': 'Details of Chore',
            'points': 'Points',
            'available': 'Is Available',
            'daily': 'Automatically Available Daily',
            'assigned_children': 'Select Children',
            'early_bonus': 'Early Bonus Points if done early',
            'bonus_end_time': 'Bonus Points Before (hour, 0-23)'
        }
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional'}),
            'bonus_end_time': forms.NumberInput(attrs={'type': 'number', 'min': '0', 'max': '23'}),
            'assigned_children': forms.CheckboxSelectMultiple()
        }

    def clean_points(self):
        # A zero-point chore can never be approved: ChoreClaim.approved doubles as
        # both the approved flag and the amount, so 0 would read as "still pending".
        points = self.cleaned_data['points']
        if points <= 0:
            raise forms.ValidationError('Points must be greater than zero.')
        return points

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('assignment_type') == 'specific' and not cleaned.get('assigned_children'):
            self.add_error('assigned_children',
                           'Select at least one child, or choose "Any Child".')
        return cleaned

    def _save_m2m(self):
        """Apply assignment_type when Django writes the m2m relations."""
        if self.cleaned_data.get('assignment_type') == 'any':
            self.cleaned_data['assigned_children'] = []
        super()._save_m2m()


class EditChoreForm(ChoreForm):
    """Same as ChoreForm, but seeds assignment_type from the existing instance."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and not self.is_bound:
            self.initial['assignment_type'] = (
                'specific' if self.instance.assigned_children.exists() else 'any')


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

    def clean_points(self):
        # See ChoreForm.clean_points: a 0-point claim can never be approved.
        points = self.cleaned_data['points']
        if points <= 0:
            raise forms.ValidationError('Points must be greater than zero.')
        return points


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


class RewardForm(forms.ModelForm):
    class Meta:
        model = Reward
        fields = ['name', 'description', 'points_cost', 'available', 'availability_type']
        help_texts = {'availability_type': None}
        labels = {
            'name': 'Reward Name',
            'description': 'Description',
            'points_cost': 'Points Cost',
            'available': 'Available',
            'availability_type': 'How many times can this be claimed?'
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional'}),
            'availability_type': forms.RadioSelect(),
        }

    def clean_points_cost(self):
        points_cost = self.cleaned_data['points_cost']
        if points_cost < 0:
            raise forms.ValidationError('Points cost cannot be negative.')
        return points_cost