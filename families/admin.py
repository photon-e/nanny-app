from django.contrib import admin

from .models import CaregiverReview, PaymentEvent


@admin.register(CaregiverReview)
class CaregiverReviewAdmin(admin.ModelAdmin):
    list_display = ("booking", "caregiver", "overall_rating", "is_visible", "flagged", "created_at")
    list_filter = ("overall_rating", "is_visible", "flagged")
    search_fields = ("caregiver__user__username", "family__user__username", "booking__id")


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ("booking", "provider", "reference", "event_type", "status", "created_at")
    list_filter = ("provider", "event_type", "status")
    search_fields = ("reference", "booking__id")
