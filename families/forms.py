from django import forms
from .models import FamilyProfile

class FamilyProfileForm(forms.ModelForm):
    class Meta:
        model = FamilyProfile
        fields = [
            'children_count',
            'care_needs',
            'location',
        ]
