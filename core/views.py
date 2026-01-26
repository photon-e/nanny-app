from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from decimal import Decimal

from .models import GeofenceCheckin, MonitoredMessage, PanicAlert
from .utils import check_geofence, generate_service_agreement_pdf, send_service_agreement_email
from families.models import Booking


def home(request):
    return render(request, "core/home.html")


@login_required
@require_http_methods(["POST"])
def geofence_checkin(request, booking_id):
    """Nanny check-in with GPS verification."""
    booking = get_object_or_404(Booking, id=booking_id)
    
    if not request.user.is_caregiver or request.user != booking.caregiver.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    actual_lat = request.POST.get('lat')
    actual_lng = request.POST.get('lng')
    
    if not actual_lat or not actual_lng:
        return JsonResponse({'error': 'Location required'}, status=400)
    
    # Get expected location from booking (you'd store this when booking is created)
    # For now, using family location as expected
    expected_lat = Decimal(str(request.POST.get('expected_lat', booking.family.location or '0')))
    expected_lng = Decimal(str(request.POST.get('expected_lng', booking.family.location or '0')))
    
    verified = check_geofence(
        float(expected_lat),
        float(expected_lng),
        float(actual_lat),
        float(actual_lng)
    )
    
    checkin = GeofenceCheckin.objects.create(
        booking=booking,
        caregiver=booking.caregiver,
        expected_lat=expected_lat,
        expected_lng=expected_lng,
        actual_lat=Decimal(actual_lat),
        actual_lng=Decimal(actual_lng),
        verified=verified
    )
    
    return JsonResponse({
        'success': True,
        'verified': verified,
        'checkin_id': checkin.id
    })


@login_required
@require_http_methods(["POST"])
def send_message(request, booking_id):
    """Send monitored message between nanny and parent."""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Verify user is part of this booking
    if request.user not in [booking.family.user, booking.caregiver.user]:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    recipient = booking.caregiver.user if request.user == booking.family.user else booking.family.user
    message_text = request.POST.get('message', '').strip()
    
    if not message_text:
        return JsonResponse({'error': 'Message required'}, status=400)
    
    msg = MonitoredMessage.objects.create(
        booking=booking,
        sender=request.user,
        recipient=recipient,
        message=message_text
    )
    
    # Auto-flag suspicious keywords (simplified)
    suspicious_keywords = ['private deal', 'cash', 'outside platform', 'direct payment']
    if any(keyword in message_text.lower() for keyword in suspicious_keywords):
        msg.flagged = True
        msg.flagged_reason = "Suspicious content detected"
        msg.save()
    
    return JsonResponse({
        'success': True,
        'message_id': msg.id,
        'flagged': msg.flagged
    })


@login_required
@require_http_methods(["POST"])
def trigger_panic_alert(request):
    """SOS/Emergency button."""
    alert_type = request.POST.get('alert_type', 'sos')
    location_lat = request.POST.get('lat')
    location_lng = request.POST.get('lng')
    message = request.POST.get('message', '')
    
    alert = PanicAlert.objects.create(
        triggered_by=request.user,
        alert_type=alert_type,
        location_lat=Decimal(location_lat) if location_lat else None,
        location_lng=Decimal(location_lng) if location_lng else None,
        message=message
    )
    
    # In production, send notifications to admins/staff
    messages.success(request, 'Panic alert sent. Help is on the way.')
    
    return JsonResponse({
        'success': True,
        'alert_id': alert.id
    })


@login_required
def generate_booking_agreement(request, booking_id):
    """Generate and email service agreement PDF."""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Verify user is part of booking
    if request.user not in [booking.family.user, booking.caregiver.user]:
        messages.error(request, 'Unauthorized.')
        return redirect('family_dashboard' if request.user.is_family else 'caregiver_dashboard')
    
    # Generate PDF
    pdf_buffer = generate_service_agreement_pdf(booking)
    
    # Send emails
    try:
        send_service_agreement_email(booking, pdf_buffer)
        messages.success(request, 'Service agreement generated and emailed to both parties.')
    except Exception as e:
        messages.error(request, f'Error generating agreement: {str(e)}')
    
    return redirect('family_dashboard' if request.user.is_family else 'caregiver_dashboard')
