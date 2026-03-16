from django import forms

from .models import CaregiverReview, FamilyProfile


class FamilyProfileForm(forms.ModelForm):
    class Meta:
        model = FamilyProfile
        fields = [
            'children_count',
            'care_needs',
            'location',
        ]


class CaregiverReviewForm(forms.ModelForm):
    class Meta:
        model = CaregiverReview
        fields = [
            "overall_rating",
            "punctuality_rating",
            "communication_rating",
            "professionalism_rating",
            "comment",
        ]
        widgets = {
            "overall_rating": forms.Select(choices=[(i, f"{i} / 5") for i in range(1, 6)]),
            "punctuality_rating": forms.Select(choices=[(i, f"{i} / 5") for i in range(1, 6)]),
            "communication_rating": forms.Select(choices=[(i, f"{i} / 5") for i in range(1, 6)]),
            "professionalism_rating": forms.Select(choices=[(i, f"{i} / 5") for i in range(1, 6)]),
            "comment": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional feedback"}),
        }
