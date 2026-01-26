from django.urls import path
from django.contrib import admin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from caregivers.models import CaregiverProfile
from .models import Dispute, PanicAlert


def approve_caregiver(request, caregiver_id):
    """Approve caregiver after manual verification."""
    if not request.user.is_staff:
        messages.error(request, "Unauthorized.")
        return redirect('admin:index')
    
    caregiver = get_object_or_404(CaregiverProfile, pk=caregiver_id)
    if caregiver.registration_level >= 3 and caregiver.guarantors.count() >= 2:
        caregiver.verified = True
        caregiver.save()
        messages.success(request, f"{caregiver.user.username} approved.")
    else:
        messages.error(request, "Requirements not met.")
    
    return redirect('admin:caregivers_caregiverprofile_changelist')


def resolve_dispute(request, dispute_id):
    """Resolve a dispute."""
    if not request.user.is_staff:
        messages.error(request, "Unauthorized.")
        return redirect('admin:index')
    
    dispute = get_object_or_404(Dispute, pk=dispute_id)
    dispute.status = 'resolved'
    dispute.resolved_by = request.user
    dispute.resolved_at = timezone.now()
    dispute.save()
    messages.success(request, "Dispute resolved.")
    
    return redirect('admin:core_dispute_changelist')


def acknowledge_panic(request, alert_id):
    """Acknowledge panic alert."""
    if not request.user.is_staff:
        messages.error(request, "Unauthorized.")
        return redirect('admin:index')
    
    alert = get_object_or_404(PanicAlert, pk=alert_id)
    alert.acknowledged = True
    alert.acknowledged_by = request.user
    alert.acknowledged_at = timezone.now()
    alert.save()
    messages.success(request, "Panic alert acknowledged.")
    
    return redirect('admin:core_panicalert_changelist')


from . import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),
    
    # Admin actions
    path('admin/approve-caregiver/<int:caregiver_id>/', approve_caregiver, name='admin:approve_caregiver'),
    path('admin/resolve-dispute/<int:dispute_id>/', resolve_dispute, name='admin:resolve_dispute'),
    path('admin/acknowledge-panic/<int:alert_id>/', acknowledge_panic, name='admin:acknowledge_panic'),
    
    # Geofencing & Chat
    path('booking/<int:booking_id>/checkin/', views.geofence_checkin, name='geofence_checkin'),
    path('booking/<int:booking_id>/message/', views.send_message, name='send_message'),
    path('booking/<int:booking_id>/agreement/', views.generate_booking_agreement, name='generate_agreement'),
    path('panic-alert/', views.trigger_panic_alert, name='panic_alert'),
]
