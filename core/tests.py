from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from caregivers.models import CaregiverProfile
from families.models import Booking, FamilyProfile
from .models import GeofenceCheckin, MonitoredMessage


User = get_user_model()


class ActiveBookingFlowTests(TestCase):
    def setUp(self):
        self.family_user = User.objects.create_user(
            username="family", password="pass123", is_family=True
        )
        self.caregiver_user = User.objects.create_user(
            username="caregiver", password="pass123", is_caregiver=True
        )
        self.other_user = User.objects.create_user(username="other", password="pass123")

        self.family_profile, _ = FamilyProfile.objects.get_or_create(user=self.family_user, defaults={"location": "Ikeja"})
        self.family_profile.location = "Ikeja"
        self.family_profile.save(update_fields=["location"])

        self.caregiver_profile, _ = CaregiverProfile.objects.get_or_create(user=self.caregiver_user)
        self.caregiver_profile.registration_level = 3
        self.caregiver_profile.phone = "1234"
        self.caregiver_profile.location = "Ikeja"
        self.caregiver_profile.code_of_conduct_signed = True
        self.caregiver_profile.save()
        self.booking = Booking.objects.create(
            family=self.family_profile,
            caregiver=self.caregiver_profile,
            amount=10000,
            payment_provider="paystack",
            service_start=timezone.now(),
            service_end=timezone.now(),
            service_location_lat=Decimal("6.524400"),
            service_location_lng=Decimal("3.379200"),
        )

    def test_family_can_view_active_booking(self):
        self.client.login(username="family", password="pass123")
        response = self.client.get(reverse("active_booking", args=[self.booking.id]))
        self.assertEqual(response.status_code, 200)

    def test_non_participant_cannot_view_active_booking(self):
        self.client.login(username="other", password="pass123")
        response = self.client.get(reverse("active_booking", args=[self.booking.id]))
        self.assertEqual(response.status_code, 302)

    def test_monitored_message_is_flagged_for_suspicious_content(self):
        self.client.login(username="family", password="pass123")
        self.client.post(
            reverse("booking_send_message", args=[self.booking.id]),
            {"message": "Let us do private deal cash outside platform"},
        )
        msg = MonitoredMessage.objects.get(booking=self.booking)
        self.assertTrue(msg.flagged)

    def test_caregiver_checkin_creates_record(self):
        self.client.login(username="caregiver", password="pass123")
        self.client.post(
            reverse("booking_checkin", args=[self.booking.id]),
            {"lat": "6.524400", "lng": "3.379200"},
        )
        checkin = GeofenceCheckin.objects.get(booking=self.booking)
        self.assertTrue(checkin.verified)
