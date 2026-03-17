import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from caregivers.models import CaregiverProfile

from .models import Booking, FamilyProfile, PaymentEvent
from .payments import build_webhook_signature


User = get_user_model()


class FamilyDashboardTests(TestCase):
    def test_dashboard_creates_missing_profile_without_error(self):
        user = User.objects.create_user(
            username="family_dashboard_user",
            password="pass12345",
            is_family=True,
        )

        self.client.login(username="family_dashboard_user", password="pass12345")
        response = self.client.get(reverse("family_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(FamilyProfile.objects.filter(user=user).exists())


class PaymentLifecycleTests(TestCase):
    def setUp(self):
        self.family_user = User.objects.create_user(
            username="family_payment_user",
            password="pass12345",
            email="family@example.com",
            is_family=True,
        )
        self.caregiver_user = User.objects.create_user(
            username="caregiver_payment_user",
            password="pass12345",
            is_caregiver=True,
        )
        self.caregiver = CaregiverProfile.objects.get(user=self.caregiver_user)
        self.caregiver.hourly_rate = 3500
        self.caregiver.is_available = True
        self.caregiver.save(update_fields=["hourly_rate", "is_available"])

    def _create_booking_and_initialize_checkout(self):
        self.client.get(reverse("create_booking", args=[self.caregiver.id]))
        booking = Booking.objects.get(family__user=self.family_user)
        self.client.get(reverse("start_booking_checkout", args=[booking.id]))
        booking.refresh_from_db()
        return booking

    def test_create_booking_redirects_to_checkout(self):
        self.client.login(username="family_payment_user", password="pass12345")

        response = self.client.get(reverse("create_booking", args=[self.caregiver.id]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/families/booking/", response.url)
        booking = Booking.objects.get(family__user=self.family_user)
        self.assertEqual(booking.status, "pending")

        self.client.get(reverse("start_booking_checkout", args=[booking.id]))
        booking.refresh_from_db()
        self.assertTrue(booking.checkout_reference)

    def test_mock_checkout_success_moves_booking_to_escrow(self):
        self.client.login(username="family_payment_user", password="pass12345")
        booking = self._create_booking_and_initialize_checkout()

        response = self.client.get(
            reverse("mock_checkout", args=[booking.id]),
            {"reference": booking.checkout_reference, "action": "success"},
        )

        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.status, "escrow")
        self.assertIsNotNone(booking.payment_verified_at)
        self.assertTrue(
            PaymentEvent.objects.filter(booking=booking, event_type="charge.success", status="processed").exists()
        )

    def test_webhook_signature_required(self):
        self.client.login(username="family_payment_user", password="pass12345")
        booking = self._create_booking_and_initialize_checkout()

        payload = {"event": "charge.success", "data": {"reference": booking.checkout_reference}}
        response = self.client.post(
            reverse("payment_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        raw_body, signature = build_webhook_signature(payload)
        response = self.client.generic(
            "POST",
            reverse("payment_webhook"),
            data=raw_body,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=signature,
        )
        self.assertEqual(response.status_code, 200)

    def test_staff_can_release_and_refund(self):
        self.client.login(username="family_payment_user", password="pass12345")
        booking = self._create_booking_and_initialize_checkout()
        self.client.get(
            reverse("mock_checkout", args=[booking.id]),
            {"reference": booking.checkout_reference, "action": "success"},
        )

        staff = User.objects.create_user(username="staff", password="pass12345", is_staff=True)
        self.client.login(username="staff", password="pass12345")

        release_response = self.client.post(reverse("release_booking", args=[booking.id]))
        self.assertEqual(release_response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.status, "released")

        new_booking = Booking.objects.create(
            family=FamilyProfile.objects.get(user=self.family_user),
            caregiver=self.caregiver,
            amount=1000,
            payment_provider="paystack",
            status="pending",
        )
        refund_response = self.client.post(reverse("refund_booking", args=[new_booking.id]))
        self.assertEqual(refund_response.status_code, 302)
        new_booking.refresh_from_db()
        self.assertEqual(new_booking.status, "refunded")
