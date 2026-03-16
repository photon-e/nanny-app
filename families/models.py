from django.conf import settings
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator

User = settings.AUTH_USER_MODEL


class FamilyProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    children_count = models.PositiveIntegerField(default=1)
    care_needs = models.TextField(blank=True)
    location = models.CharField(max_length=255)

    # New: secure booking / platform features
    default_payment_provider = models.CharField(
        max_length=50,
        blank=True,
        help_text="Preferred provider: paystack/flutterwave/opay/moniepoint",
    )

    def __str__(self):
        return self.user.username


class AuthorizedPickup(models.Model):
    """People allowed to pick up the child (driver, auntie, etc.)."""

    family = models.ForeignKey(FamilyProfile, on_delete=models.CASCADE, related_name="authorized_pickups")
    full_name = models.CharField(max_length=255)
    relationship = models.CharField(max_length=100, blank=True)
    photo = models.ImageField(upload_to="authorized_pickups/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.family.user.username})"


class IncidentReport(models.Model):
    """Digital incident log from parents."""

    LATE = "late_arrival"
    THEFT = "theft_suspicion"
    MISCONDUCT = "misconduct"
    INCIDENT_CHOICES = [
        (LATE, "Late Arrival"),
        (THEFT, "Theft Suspicion"),
        (MISCONDUCT, "Misconduct"),
    ]

    family = models.ForeignKey(FamilyProfile, on_delete=models.CASCADE, related_name="incidents")
    caregiver = models.ForeignKey(
        "caregivers.CaregiverProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incidents",
    )
    incident_type = models.CharField(max_length=50, choices=INCIDENT_CHOICES)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_incident_type_display()} - {self.family.user.username}"


class Booking(models.Model):
    """Secure booking & escrow record."""

    PROVIDER_CHOICES = [
        ("paystack", "Paystack"),
        ("flutterwave", "Flutterwave"),
        ("opay", "Opay"),
        ("moniepoint", "Moniepoint"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending Payment"),
        ("escrow", "In Escrow"),
        ("released", "Released to Nanny"),
        ("refunded", "Refunded"),
        ("cancelled", "Cancelled"),
    ]

    family = models.ForeignKey(FamilyProfile, on_delete=models.CASCADE, related_name="bookings")
    caregiver = models.ForeignKey(
        "caregivers.CaregiverProfile", on_delete=models.CASCADE, related_name="bookings"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    service_start = models.DateTimeField(null=True, blank=True)
    service_end = models.DateTimeField(null=True, blank=True)
    service_location_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    service_location_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    payment_provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_reference = models.CharField(
        max_length=255, blank=True, help_text="Gateway reference / transaction ID"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    service_date = models.DateField(null=True, blank=True)

    # Commission fields (used by admin Commission Tracker)
    agent_commission = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, help_text="Platform/agent fee"
    )
    caregiver_payout = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, help_text="Net payout to caregiver"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Booking {self.id} - {self.family.user.username} → {self.caregiver.user.username}"


class CaregiverReview(models.Model):
    """Post-booking family feedback for a caregiver."""

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="review")
    family = models.ForeignKey(FamilyProfile, on_delete=models.CASCADE, related_name="caregiver_reviews")
    caregiver = models.ForeignKey(
        "caregivers.CaregiverProfile", on_delete=models.CASCADE, related_name="reviews"
    )
    overall_rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    punctuality_rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    communication_rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    professionalism_rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    is_visible = models.BooleanField(default=True)
    flagged = models.BooleanField(default=False)
    flag_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Review for Booking {self.booking_id} ({self.overall_rating}/5)"
