from datetime import date

from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


class CaregiverProfile(models.Model):
    REGISTRATION_LEVEL_CHOICES = [
        (1, "Level 1 - Basic"),
        (2, "Level 2 - Identity"),
        (3, "Level 3 - Guarantors"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    hourly_rate = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)

    # Verified badge is controlled by training completion (see TrainingCompletion logic in views)
    verified = models.BooleanField(default=False)

    profile_image = models.ImageField(upload_to="caregiver_photos/", blank=True, null=True)

    # Tiered Registration Fields
    registration_level = models.IntegerField(choices=REGISTRATION_LEVEL_CHOICES, default=1)
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    nin_document = models.FileField(upload_to="nin_documents/", blank=True, null=True)
    selfie_photo = models.ImageField(upload_to="selfie_photos/", blank=True, null=True)

    # Platform features
    is_available = models.BooleanField(default=False, help_text="Toggle to control visibility to parents")
    code_of_conduct_signed = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

    def calculate_age(self):
        if not self.date_of_birth:
            return None
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    def is_at_least_18(self):
        age = self.calculate_age()
        return age is not None and age >= 18

    def can_proceed_to_level_2(self):
        return (
            self.registration_level >= 1
            and self.user.first_name
            and self.user.last_name
            and self.phone
            and self.date_of_birth
            and self.is_at_least_18()
            and self.location
        )

    def can_proceed_to_level_3(self):
        return self.registration_level >= 2 and self.nin_document and self.selfie_photo


class Guarantor(models.Model):
    caregiver = models.ForeignKey(CaregiverProfile, on_delete=models.CASCADE, related_name="guarantors")
    full_name = models.CharField(max_length=255)
    nin = models.CharField(max_length=20)
    phone = models.CharField(max_length=20)
    phone_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.full_name} - Guarantor for {self.caregiver.user.username}"


class CodeOfConductSignature(models.Model):
    caregiver = models.OneToOneField(
        CaregiverProfile, on_delete=models.CASCADE, related_name="code_of_conduct"
    )
    signed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-signed_at"]

    def __str__(self):
        return f"Code of Conduct signed by {self.caregiver.user.username} on {self.signed_at.date()}"


class TrainingModule(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    content = models.TextField(help_text="Full training content")
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self):
        return self.title


class TrainingQuiz(models.Model):
    module = models.ForeignKey(TrainingModule, on_delete=models.CASCADE, related_name="questions")
    question = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255, blank=True)
    option_d = models.CharField(max_length=255, blank=True)
    correct_answer = models.CharField(max_length=1, choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")])
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.module.title} - Q{self.order + 1}"


class TrainingCompletion(models.Model):
    caregiver = models.ForeignKey(CaregiverProfile, on_delete=models.CASCADE, related_name="training_completions")
    module = models.ForeignKey(TrainingModule, on_delete=models.CASCADE, related_name="completions")
    passed = models.BooleanField(default=False)
    score = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["caregiver", "module"]
        ordering = ["-completed_at"]

    def __str__(self):
        status = "Passed" if self.passed else "Failed"
        return f"{self.caregiver.user.username} - {self.module.title} ({status})"


class EarningsWallet(models.Model):
    PAYOUT_STATUS_CHOICES = [
        ("pending", "Pending (24-hour security window)"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    caregiver = models.ForeignKey(CaregiverProfile, on_delete=models.CASCADE, related_name="earnings")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    payout_status = models.CharField(max_length=20, choices=PAYOUT_STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.caregiver.user.username} - ${self.amount} ({self.payout_status})"