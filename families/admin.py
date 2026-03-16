from django.contrib import admin

from .models import CaregiverReview


@admin.register(CaregiverReview)
class CaregiverReviewAdmin(admin.ModelAdmin):
    list_display = ("booking", "caregiver", "overall_rating", "is_visible", "flagged", "created_at")
    list_filter = ("overall_rating", "is_visible", "flagged")
    search_fields = ("caregiver__user__username", "family__user__username", "booking__id")
