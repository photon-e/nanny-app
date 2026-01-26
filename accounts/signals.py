from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User
from caregivers.models import CaregiverProfile
from families.models import FamilyProfile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.is_caregiver:
            CaregiverProfile.objects.create(user=instance)
        elif instance.is_family:
            FamilyProfile.objects.create(user=instance)
