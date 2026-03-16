from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from families.models import Booking, CaregiverReview, FamilyProfile

from .models import CaregiverProfile


User = get_user_model()


class CaregiverSearchTests(TestCase):
    def setUp(self):
        caregiver_user = User.objects.create_user(username="cg1", password="pass123")
        family_user = User.objects.create_user(username="fam1", password="pass123", is_family=True)
        self.matching = CaregiverProfile.objects.create(
            user=caregiver_user,
            is_available=True,
            location="Lagos",
            bio="Infant care expert",
            experience_years=4,
            hourly_rate="2500.00",
        )
        self.family, _ = FamilyProfile.objects.get_or_create(user=family_user, defaults={"location": "Lagos"})
        self.family.location = "Lagos"
        self.family.save(update_fields=["location"])

        booking = Booking.objects.create(
            family=self.family,
            caregiver=self.matching,
            amount=10000,
            payment_provider="paystack",
            status="released",
        )
        CaregiverReview.objects.create(
            booking=booking,
            family=self.family,
            caregiver=self.matching,
            overall_rating=5,
            punctuality_rating=5,
            communication_rating=4,
            professionalism_rating=5,
            comment="Reliable and kind",
        )

    def test_public_search_handles_invalid_numeric_filters(self):
        response = self.client.get(
            reverse("caregiver_list"),
            {"max_rate": "abc", "min_exp": "xyz"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.matching.user.username)

    def test_public_search_filters_by_query_location_and_limits(self):
        response = self.client.get(
            reverse("caregiver_list"),
            {"q": "infant", "location": "lagos", "min_exp": "3", "max_rate": "3000"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.matching.user.username)

    def test_caregiver_list_shows_rating_summary(self):
        response = self.client.get(reverse("caregiver_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "5.0/5")

    def test_caregiver_detail_shows_review_comment(self):
        response = self.client.get(reverse("caregiver_detail", args=[self.matching.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reliable and kind")
