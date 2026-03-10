from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from families.models import FamilyProfile

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
            verified=True,
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

    def test_family_user_sees_all_caregivers_including_unavailable(self):
        unavailable_user = User.objects.create_user(username="cg_unavailable", password="pass123")
        CaregiverProfile.objects.create(
            user=unavailable_user,
            is_available=False,
            location="Lagos",
            experience_years=1,
        )

        family_user = User.objects.create_user(username="family1", password="pass123", is_family=True)
        FamilyProfile.objects.update_or_create(user=family_user, defaults={"location": "Lagos"})

        self.client.login(username="family1", password="pass123")
        response = self.client.get(reverse("caregiver_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cg_unavailable")

    def test_family_user_ordered_by_location_proximity(self):
        near_user = User.objects.create_user(username="cg_near", password="pass123")
        far_user = User.objects.create_user(username="cg_far", password="pass123")

        CaregiverProfile.objects.create(
            user=near_user,
            is_available=False,
            location="Abuja",
            experience_years=2,
        )
        CaregiverProfile.objects.create(
            user=far_user,
            is_available=True,
            location="Kano",
            experience_years=6,
        )

        family_user = User.objects.create_user(username="family2", password="pass123", is_family=True)
        FamilyProfile.objects.update_or_create(user=family_user, defaults={"location": "Abuja"})

        self.client.login(username="family2", password="pass123")
        response = self.client.get(reverse("caregiver_list"))

        self.assertEqual(response.status_code, 200)
        caregivers = list(response.context["caregivers"])
        usernames = [c.user.username for c in caregivers]

        self.assertLess(usernames.index("cg_near"), usernames.index("cg_far"))
