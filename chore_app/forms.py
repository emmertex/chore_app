from chore_app.models import Chore, User, PointLog, ChoreClaim, Settings
from django import forms

class ChoreForm(forms.ModelForm):
    class Meta:
        model = Chore
        fields = ['name', 'points', 'available', 'daily', 'persistent', 'earlyBonus']

class EditChoreForm(forms.ModelForm):
    class Meta:
        model = Chore
        fields = ['name', 'points', 'available', 'daily', 'persistent', 'earlyBonus']

class PointAdjustmentForm(forms.ModelForm):
    class Meta:
        model = PointLog
        fields = ['points_change', 'reason']

class PocketMoneyAdjustmentForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['pocket_money']

class CustomChildChore(forms.ModelForm):
    class Meta:
        model = ChoreClaim
        fields = ['choreName', 'points', 'comment']

class EditSettingsForm(forms.ModelForm):
    class Meta:
        model = Settings
        fields = ['name', 'value']