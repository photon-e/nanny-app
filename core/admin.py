from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Sum, Count, Q

from .models import Blacklist, Dispute, PanicAlert, GeofenceCheckin, ServiceAgreement, MonitoredMessage
from families.models import Booking, IncidentReport, AuthorizedPickup, FamilyProfile


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    """Dispute Management Dashboard."""
    
    list_display = [
        'id', 'incident', 'status', 'caregiver_payout_frozen', 
        'family_account_banned', 'created_at', 'actions'
    ]
    list_filter = ['status', 'caregiver_payout_frozen', 'family_account_banned', 'created_at']
    search_fields = ['incident__family__user__username', 'incident__caregiver__user__username']
    readonly_fields = ['created_at', 'resolved_at']
    
    def actions(self, obj):
        """Quick action buttons."""
        buttons = []
        if obj.status != 'resolved':
            resolve_url = reverse('admin:resolve_dispute', args=[obj.pk])
            buttons.append(f'<a href="{resolve_url}" class="button">Resolve</a>')
        return format_html(" ".join(buttons))
    actions.short_description = "Actions"
    
    actions = ['freeze_caregiver_payout', 'ban_family_account', 'dismiss_disputes']
    
    def freeze_caregiver_payout(self, request, queryset):
        """Freeze caregiver payouts."""
        for dispute in queryset:
            dispute.caregiver_payout_frozen = True
            dispute.save()
            if dispute.incident.caregiver:
                dispute.incident.caregiver.earnings.filter(payout_status='pending').update(payout_status='failed')
        self.message_user(request, f"Payouts frozen for {queryset.count()} disputes.")
    freeze_caregiver_payout.short_description = "Freeze caregiver payouts"
    
    def ban_family_account(self, request, queryset):
        """Ban family accounts."""
        for dispute in queryset:
            dispute.family_account_banned = True
            dispute.save()
            dispute.incident.family.user.is_active = False
            dispute.incident.family.user.save()
        self.message_user(request, f"{queryset.count()} family accounts banned.")
    ban_family_account.short_description = "Ban family accounts"
    
    def dismiss_disputes(self, request, queryset):
        """Dismiss disputes."""
        queryset.update(status='dismissed', resolved_by=request.user, resolved_at=timezone.now())
        self.message_user(request, f"{queryset.count()} disputes dismissed.")


@admin.register(Blacklist)
class BlacklistAdmin(admin.ModelAdmin):
    """Blacklist Manager - Database of banned nannies."""
    
    list_display = ['nin', 'reason', 'banned_by', 'banned_at']
    list_filter = ['banned_at', 'reason']
    search_fields = ['nin', 'reason', 'notes']
    readonly_fields = ['banned_at']


@admin.register(PanicAlert)
class PanicAlertAdmin(admin.ModelAdmin):
    """Panic Alert Log - Real-time SOS notifications."""
    
    list_display = [
        'id', 'triggered_by', 'alert_type', 'location_lat', 
        'location_lng', 'acknowledged', 'created_at', 'acknowledge_button'
    ]
    list_filter = ['alert_type', 'acknowledged', 'created_at']
    search_fields = ['triggered_by__username', 'message']
    readonly_fields = ['created_at']
    
    def acknowledge_button(self, obj):
        """Acknowledge panic alert."""
        if obj.acknowledged:
            return format_html('<span style="color: green;">✓ Acknowledged</span>')
        url = reverse('admin:acknowledge_panic', args=[obj.pk])
        return format_html('<a href="{}" class="button">Acknowledge</a>', url)
    acknowledge_button.short_description = "Actions"


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """Commission Tracker - Shows agent fees and payouts."""
    
    list_display = [
        'id', 'family', 'caregiver', 'amount', 
        'agent_commission', 'caregiver_payout', 'status', 'created_at'
    ]
    list_filter = ['status', 'payment_provider', 'created_at']
    search_fields = ['family__user__username', 'caregiver__user__username']
    readonly_fields = ['created_at']
    
    def save_model(self, request, obj, form, change):
        """Auto-calculate commission on save."""
        if not change or 'amount' in form.changed_data:
            # Calculate 15% commission (configurable)
            commission_rate = 0.15
            obj.agent_commission = obj.amount * commission_rate
            obj.caregiver_payout = obj.amount - obj.agent_commission
        super().save_model(request, obj, form, change)


@admin.register(GeofenceCheckin)
class GeofenceCheckinAdmin(admin.ModelAdmin):
    """Geofencing Check-ins."""
    
    list_display = ['id', 'booking', 'caregiver', 'verified', 'checkin_time']
    list_filter = ['verified', 'checkin_time']
    search_fields = ['caregiver__user__username', 'booking__family__user__username']


@admin.register(ServiceAgreement)
class ServiceAgreementAdmin(admin.ModelAdmin):
    """Service Agreement PDFs."""
    
    list_display = ['id', 'booking', 'generated_at', 'sent_to_family', 'sent_to_caregiver']
    list_filter = ['generated_at', 'sent_to_family', 'sent_to_caregiver']
    search_fields = ['booking__family__user__username', 'booking__caregiver__user__username']


@admin.register(MonitoredMessage)
class MonitoredMessageAdmin(admin.ModelAdmin):
    """Monitored Chat Messages."""
    
    list_display = ['id', 'sender', 'recipient', 'booking', 'flagged', 'created_at']
    list_filter = ['flagged', 'created_at']
    search_fields = ['sender__username', 'recipient__username', 'message']
    readonly_fields = ['created_at']
    
    actions = ['flag_selected', 'unflag_selected']
    
    def flag_selected(self, request, queryset):
        """Flag messages for review."""
        queryset.update(flagged=True)
        self.message_user(request, f"{queryset.count()} messages flagged.")
    flag_selected.short_description = "Flag selected messages"
    
    def unflag_selected(self, request, queryset):
        """Unflag messages."""
        queryset.update(flagged=False)
        self.message_user(request, f"{queryset.count()} messages unflagged.")


# Register families models
@admin.register(AuthorizedPickup)
class AuthorizedPickupAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'family', 'relationship', 'created_at']
    list_filter = ['created_at']
    search_fields = ['full_name', 'family__user__username']

@admin.register(IncidentReport)
class IncidentReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'family', 'caregiver', 'incident_type', 'resolved', 'created_at']
    list_filter = ['incident_type', 'resolved', 'created_at']
    search_fields = ['family__user__username', 'caregiver__user__username', 'description']

@admin.register(FamilyProfile)
class FamilyProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'location', 'children_count', 'default_payment_provider']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'location']
