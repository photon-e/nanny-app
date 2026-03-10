from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import CaregiverProfile


User = get_user_model()


class CaregiverSearchTests(TestCase):
    def setUp(self):
        caregiver_user = User.objects.create_user(username="cg1", password="pass123")
        self.matching = CaregiverProfile.objects.create(
            user=caregiver_user,
            is_available=True,
            location="Lagos",
            bio="Infant care expert",
            experience_years=4,
            hourly_rate="2500.00",
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
