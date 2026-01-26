from allauth.account.forms import SignupForm
from families.models import FamilyProfile
from caregivers.models import CaregiverProfile


class FamilySignupForm(SignupForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none'
            })

    def save(self, request):
        user = super().save(request)
        user.is_family = True
        user.save()

        FamilyProfile.objects.create(user=user)
        return user



class CaregiverSignupForm(SignupForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none'
            })

    def save(self, request):
        user = super().save(request)
        user.is_caregiver = True
        user.save()

        CaregiverProfile.objects.create(user=user)
        return user
