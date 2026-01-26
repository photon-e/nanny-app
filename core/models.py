from django.conf import settings
from django.db import models
from django.utils import timezone

User = settings.AUTH_USER_MODEL


class Blacklist(models.Model):
    """Blacklist manager - prevents banned nannies from re-registering with same NIN."""
    
    nin = models.CharField(max_length=20, unique=True, db_index=True)
    reason = models.CharField(max_length=255, help_text="Reason for blacklist (theft, abuse, etc.)")
    banned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    banned_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-banned_at']
    
    def __str__(self):
        return f"NIN: {self.nin} - {self.reason}"


class Dispute(models.Model):
    """Dispute management - tracks reported incidents and admin actions."""
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('investigating', 'Under Investigation'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    
    incident = models.OneToOneField(
        'families.IncidentReport',
        on_delete=models.CASCADE,
        related_name='dispute'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    admin_notes = models.TextField(blank=True)
    caregiver_payout_frozen = models.BooleanField(default=False)
    family_account_banned = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_disputes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Dispute #{self.id} - {self.get_status_display()}"


class PanicAlert(models.Model):
    """Panic Alert Log - real-time SOS/Emergency button notifications."""
    
    ALERT_TYPES = [
        ('sos', 'SOS/Emergency'),
        ('safety', 'Safety Concern'),
        ('medical', 'Medical Emergency'),
    ]
    
    triggered_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='panic_alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES, default='sos')
    location_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    message = models.TextField(blank=True)
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='acknowledged_alerts')
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Panic Alert - {self.get_alert_type_display()} by {self.triggered_by.username}"


class GeofenceCheckin(models.Model):
    """Automatic Geofencing - tracks nanny check-ins at parent's location."""
    
    booking = models.ForeignKey('families.Booking', on_delete=models.CASCADE, related_name='checkins')
    caregiver = models.ForeignKey('caregivers.CaregiverProfile', on_delete=models.CASCADE, related_name='checkins')
    expected_lat = models.DecimalField(max_digits=9, decimal_places=6)
    expected_lng = models.DecimalField(max_digits=9, decimal_places=6)
    actual_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    actual_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    verified = models.BooleanField(default=False, help_text="GPS confirmed at location")
    checkin_time = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-checkin_time']
    
    def __str__(self):
        status = "Verified" if self.verified else "Pending"
        return f"Check-in {self.id} - {status}"


class ServiceAgreement(models.Model):
    """PDF Generator - Service Agreement contracts for bookings."""
    
    booking = models.OneToOneField('families.Booking', on_delete=models.CASCADE, related_name='agreement')
    pdf_file = models.FileField(upload_to='service_agreements/', blank=True, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    sent_to_family = models.BooleanField(default=False)
    sent_to_caregiver = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Service Agreement for Booking {self.booking.id}"


class MonitoredMessage(models.Model):
    """Nanny-Parent Chat (Monitored) - all communication stays in app."""
    
    booking = models.ForeignKey('families.Booking', on_delete=models.CASCADE, related_name='monitored_messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_monitored_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_monitored_messages')
    message = models.TextField()
    flagged = models.BooleanField(default=False, help_text="Flagged for review (harassment, private deal solicitation)")
    flagged_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Message from {self.sender.username} to {self.recipient.username}"
