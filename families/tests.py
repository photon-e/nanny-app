from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import FamilyProfile


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
