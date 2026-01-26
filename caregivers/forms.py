from django import forms
from django.core.exceptions import ValidationError
from datetime import date
from .models import CaregiverProfile, Guarantor, TrainingModule, TrainingQuiz, TrainingCompletion

class CaregiverProfileForm(forms.ModelForm):
    class Meta:
        model = CaregiverProfile
        fields = [
            "bio",
            "location",
            "experience_years",
            "hourly_rate",
            "profile_image",
        ]


class Level1RegistrationForm(forms.Form):
    """Level 1: Basic Information"""
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:outline-none',
            'placeholder': 'Enter your first name'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:outline-none',
            'placeholder': 'Enter your last name'
        })
    )
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:outline-none',
            'placeholder': 'e.g., +234 800 000 0000'
        })
    )
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:outline-none',
            'type': 'date',
            'max': str(date.today().replace(year=date.today().year - 18))
        }),
        help_text='You must be at least 18 years old'
    )
    
    def clean_date_of_birth(self):
        """Validate that the person is at least 18 years old"""
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth:
            today = date.today()
            age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
            if age < 18:
                raise ValidationError('You must be at least 18 years old to register.')
        return date_of_birth
    location = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:outline-none',
            'placeholder': 'Enter your location'
        })
    )


class Level2RegistrationForm(forms.ModelForm):
    """Level 2: Identity Verification"""
    class Meta:
        model = CaregiverProfile
        fields = ['nin_document', 'selfie_photo']
        widgets = {
            'nin_document': forms.FileInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:outline-none',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
            'selfie_photo': forms.FileInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:outline-none',
                'accept': 'image/*',
                'capture': 'user'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nin_document'].required = True
        self.fields['selfie_photo'].required = True
        self.fields['nin_document'].label = 'NIN Document (Upload photo/scan of your National Identification Number)'
        self.fields['selfie_photo'].label = 'Live Selfie (Take a photo to match your NIN photo)'


class Level3RegistrationForm(forms.Form):
    """Level 3: Guarantors Information"""
    guarantor1_name = forms.CharField(
        max_length=255,
        label='Guarantor 1 - Full Name',
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:outline-none',
            'placeholder': 'Enter full name'
        })
    )
    guarantor1_nin = forms.CharField(
        max_length=20,
        label='Guarantor 1 - NIN',
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:outline-none',
            'placeholder': 'Enter NIN'
        })
    )
    guarantor1_phone = forms.CharField(
        max_length=20,
        label='Guarantor 1 - Phone Number',
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:outline-none',
            'placeholder': 'e.g., +234 800 000 0000'
        })
    )
    
    guarantor2_name = forms.CharField(
        max_length=255,
        label='Guarantor 2 - Full Name',
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:outline-none',
            'placeholder': 'Enter full name'
        })
    )
    guarantor2_nin = forms.CharField(
        max_length=20,
        label='Guarantor 2 - NIN',
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:outline-none',
            'placeholder': 'Enter NIN'
        })
    )
    guarantor2_phone = forms.CharField(
        max_length=20,
        label='Guarantor 2 - Phone Number',
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:outline-none',
            'placeholder': 'e.g., +234 800 000 0000'
        })
    )


class CodeOfConductForm(forms.Form):
    """Code of Conduct e-signature form"""
    agree = forms.BooleanField(
        required=True,
        label="I have read and agree to the Code of Conduct",
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
        })
    )
    signature = forms.CharField(
        max_length=255,
        required=True,
        label="E-Signature (Type your full name)",
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:outline-none',
            'placeholder': 'Enter your full name to sign'
        })
    )


class TrainingQuizForm(forms.Form):
    """Dynamic form for training quiz"""
    
    def __init__(self, *args, **kwargs):
        questions = kwargs.pop('questions', [])
        super().__init__(*args, **kwargs)
        
        for question in questions:
            choices = [
                ('A', question.option_a),
                ('B', question.option_b),
            ]
            if question.option_c:
                choices.append(('C', question.option_c))
            if question.option_d:
                choices.append(('D', question.option_d))
            
            self.fields[f'question_{question.id}'] = forms.ChoiceField(
                label=question.question,
                choices=choices,
                widget=forms.RadioSelect(attrs={
                    'class': 'mr-2'
                })
            )