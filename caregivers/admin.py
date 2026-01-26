from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    CaregiverProfile, Guarantor, CodeOfConductSignature,
    TrainingModule, TrainingQuiz, TrainingCompletion, EarningsWallet
)

@admin.register(CaregiverProfile)
class CaregiverProfileAdmin(admin.ModelAdmin):
    """Verification Queue - List of new nannies awaiting approval."""
    
    list_display = [
        'user', 'registration_level', 'phone', 'location', 
        'verified', 'is_available', 'code_of_conduct_signed', 
        'verification_status', 'approve_button'
    ]
    list_filter = ['registration_level', 'verified', 'is_available', 'code_of_conduct_signed']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'phone', 'location']
    readonly_fields = ['verification_status']
    
    def verification_status(self, obj):
        """Show verification checklist."""
        checks = []
        if obj.registration_level >= 3:
            checks.append("✓ Registration Complete")
        if obj.code_of_conduct_signed:
            checks.append("✓ Code of Conduct Signed")
        if obj.verified:
            checks.append("✓ Training Passed")
        if obj.guarantors.count() >= 2:
            checks.append("✓ Guarantors Added")
        
        if len(checks) == 4:
            return format_html('<span style="color: green;">{}</span>', " | ".join(checks))
        return " | ".join(checks) if checks else "Pending"
    verification_status.short_description = "Verification Status"
    
    def approve_button(self, obj):
        """Manual approve button - only after calling guarantors."""
        if obj.verified:
            return format_html('<span style="color: green;">✓ Approved</span>')
        
        # Check if all requirements met
        if obj.registration_level >= 3 and obj.guarantors.count() >= 2:
            url = reverse('admin:approve_caregiver', args=[obj.pk])
            return format_html('<a href="{}" class="button">Approve</a>', url)
        return "Requirements not met"
    approve_button.short_description = "Actions"
    
    actions = ['approve_selected', 'freeze_payouts', 'ban_selected']
    
    def approve_selected(self, request, queryset):
        """Bulk approve after manual verification."""
        count = 0
        for caregiver in queryset:
            if caregiver.registration_level >= 3 and caregiver.guarantors.count() >= 2:
                caregiver.verified = True
                caregiver.save()
                count += 1
        self.message_user(request, f"{count} caregivers approved.")
    approve_selected.short_description = "Approve selected caregivers"
    
    def freeze_payouts(self, request, queryset):
        """Freeze payouts for selected caregivers."""
        for caregiver in queryset:
            # Mark all pending earnings as frozen
            caregiver.earnings.filter(payout_status='pending').update(payout_status='failed')
        self.message_user(request, f"Payouts frozen for {queryset.count()} caregivers.")
    freeze_payouts.short_description = "Freeze payouts"
    
    def ban_selected(self, request, queryset):
        """Ban caregivers and add to blacklist."""
        from core.models import Blacklist
        count = 0
        for caregiver in queryset:
            # Try to get NIN from guarantors or use placeholder
            nin = None
            if caregiver.guarantors.exists():
                nin = caregiver.guarantors.first().nin
            if not nin:
                nin = f"EXTRACT_{caregiver.id}"
            
            Blacklist.objects.get_or_create(
                nin=nin,
                defaults={
                    'reason': 'Admin ban',
                    'banned_by': request.user,
                    'notes': f'Banned via admin action'
                }
            )
            caregiver.is_available = False
            caregiver.save()
            count += 1
        self.message_user(request, f"{count} caregivers banned and added to blacklist.")
    ban_selected.short_description = "Ban and blacklist selected"

@admin.register(Guarantor)
class GuarantorAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'caregiver', 'nin', 'phone', 'phone_verified', 'created_at']
    list_filter = ['phone_verified', 'created_at']
    search_fields = ['full_name', 'nin', 'phone', 'caregiver__user__username']

@admin.register(CodeOfConductSignature)
class CodeOfConductSignatureAdmin(admin.ModelAdmin):
    list_display = ['caregiver', 'signed_at', 'ip_address']
    list_filter = ['signed_at']
    search_fields = ['caregiver__user__username']

@admin.register(TrainingModule)
class TrainingModuleAdmin(admin.ModelAdmin):
    list_display = ['title', 'order', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'description']

@admin.register(TrainingQuiz)
class TrainingQuizAdmin(admin.ModelAdmin):
    list_display = ['module', 'question', 'correct_answer', 'order']
    list_filter = ['module']
    search_fields = ['question', 'module__title']

@admin.register(TrainingCompletion)
class TrainingCompletionAdmin(admin.ModelAdmin):
    list_display = ['caregiver', 'module', 'passed', 'score', 'total_questions', 'completed_at']
    list_filter = ['passed', 'completed_at']
    search_fields = ['caregiver__user__username', 'module__title']

@admin.register(EarningsWallet)
class EarningsWalletAdmin(admin.ModelAdmin):
    list_display = ['caregiver', 'amount', 'description', 'payout_status', 'created_at', 'paid_at']
    list_filter = ['payout_status', 'created_at']
    search_fields = ['caregiver__user__username', 'description']
