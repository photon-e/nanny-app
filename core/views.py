from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from families.forms import CaregiverReviewForm
from families.models import Booking
from .models import GeofenceCheckin, MonitoredMessage, PanicAlert
from .utils import check_geofence, generate_service_agreement_pdf, send_service_agreement_email


SUSPICIOUS_KEYWORDS = ["private deal", "cash", "outside platform", "direct payment"]


def home(request):
    return render(request, "core/home.html")


def _get_accessible_booking(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related("family__user", "caregiver__user"),
        id=booking_id,
    )
    if request.user not in [booking.family.user, booking.caregiver.user]:
        return None
    return booking


def _build_booking_timeline(booking):
    has_checkin = booking.checkins.exists()
    has_verified_checkin = booking.checkins.filter(verified=True).exists()
    has_chat = booking.monitored_messages.exists()

    return [
        {"label": "Booking Created", "done": True, "detail": booking.created_at},
        {"label": "Payment Secured in Escrow", "done": booking.status in ["escrow", "released"], "detail": booking.get_status_display()},
        {"label": "Caregiver Check-in Logged", "done": has_checkin, "detail": "GPS check-in submitted" if has_checkin else "Pending"},
        {"label": "GPS Verified", "done": has_verified_checkin, "detail": "Within geofence" if has_verified_checkin else "Not verified yet"},
        {"label": "Monitored Chat Active", "done": has_chat, "detail": "Messages exchanged" if has_chat else "No messages yet"},
    ]


@login_required
def active_booking(request, booking_id):
    booking = _get_accessible_booking(request, booking_id)
    if booking is None:
        messages.error(request, "Unauthorized.")
        return redirect("/")

    monitored_messages = booking.monitored_messages.select_related("sender", "recipient").order_by("created_at")
    timeline_steps = _build_booking_timeline(booking)
    latest_checkin = booking.checkins.order_by("-checkin_time").first()

    return render(
        request,
        "core/active_booking.html",
        {
            "booking": booking,
            "timeline_steps": timeline_steps,
            "monitored_messages": monitored_messages,
            "latest_checkin": latest_checkin,
            "can_checkin": request.user == booking.caregiver.user,
            "can_review": request.user == booking.family.user and booking.status == "released",
            "existing_review": getattr(booking, "review", None),
            "review_form": CaregiverReviewForm(),
        },
    )


@login_required
@require_http_methods(["POST"])
def booking_submit_review(request, booking_id):
    booking = _get_accessible_booking(request, booking_id)
    if booking is None or request.user != booking.family.user:
        messages.error(request, "Unauthorized.")
        return redirect("/")

    if booking.status != "released":
        messages.error(request, "You can only review completed bookings.")
        return redirect("active_booking", booking_id=booking.id)

    if hasattr(booking, "review"):
        messages.info(request, "A review has already been submitted for this booking.")
        return redirect("active_booking", booking_id=booking.id)

    form = CaregiverReviewForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please provide valid ratings before submitting your review.")
        return redirect("active_booking", booking_id=booking.id)

    review = form.save(commit=False)
    review.booking = booking
    review.family = booking.family
    review.caregiver = booking.caregiver

    if review.overall_rating <= 2:
        review.flagged = True
        review.flag_reason = "Low rating - suggest family follow-up"

    review.save()
    messages.success(request, "Thanks! Your review has been submitted.")

    if review.overall_rating <= 2:
        messages.warning(
            request,
            "If this issue involved safety or misconduct, please file an incident report for investigation.",
        )

    return redirect("active_booking", booking_id=booking.id)


@login_required
@require_http_methods(["POST"])
def booking_checkin(request, booking_id):
    booking = _get_accessible_booking(request, booking_id)
    if booking is None or request.user != booking.caregiver.user:
        messages.error(request, "Unauthorized.")
        return redirect("/")

    if booking.service_location_lat is None or booking.service_location_lng is None:
        messages.error(request, "Service location is not configured for this booking yet.")
        return redirect("active_booking", booking_id=booking.id)

    try:
        actual_lat = Decimal(str(request.POST.get("lat", "")).strip())
        actual_lng = Decimal(str(request.POST.get("lng", "")).strip())
    except (InvalidOperation, TypeError):
        messages.error(request, "Valid latitude and longitude are required.")
        return redirect("active_booking", booking_id=booking.id)

    verified = check_geofence(
        float(booking.service_location_lat),
        float(booking.service_location_lng),
        float(actual_lat),
        float(actual_lng),
    )

    GeofenceCheckin.objects.create(
        booking=booking,
        caregiver=booking.caregiver,
        expected_lat=booking.service_location_lat,
        expected_lng=booking.service_location_lng,
        actual_lat=actual_lat,
        actual_lng=actual_lng,
        verified=verified,
    )

    if verified:
        messages.success(request, "Check-in verified successfully.")
    else:
        messages.warning(request, "Check-in recorded but outside configured geofence.")

    return redirect("active_booking", booking_id=booking.id)


@login_required
@require_http_methods(["POST"])
def booking_send_message(request, booking_id):
    booking = _get_accessible_booking(request, booking_id)
    if booking is None:
        messages.error(request, "Unauthorized.")
        return redirect("/")

    message_text = request.POST.get("message", "").strip()
    if not message_text:
        messages.error(request, "Message is required.")
        return redirect("active_booking", booking_id=booking.id)

    recipient = booking.caregiver.user if request.user == booking.family.user else booking.family.user
    msg = MonitoredMessage.objects.create(
        booking=booking,
        sender=request.user,
        recipient=recipient,
        message=message_text,
    )

    if any(keyword in message_text.lower() for keyword in SUSPICIOUS_KEYWORDS):
        msg.flagged = True
        msg.flagged_reason = "Suspicious content detected"
        msg.save(update_fields=["flagged", "flagged_reason"])

    return redirect("active_booking", booking_id=booking.id)


@login_required
@require_http_methods(["POST"])
def trigger_panic_alert(request):
    """SOS/Emergency button."""
    alert_type = request.POST.get("alert_type", "sos")
    location_lat = request.POST.get("lat")
    location_lng = request.POST.get("lng")
    message_text = request.POST.get("message", "")

    alert = PanicAlert.objects.create(
        triggered_by=request.user,
        alert_type=alert_type,
        location_lat=Decimal(location_lat) if location_lat else None,
        location_lng=Decimal(location_lng) if location_lng else None,
        message=message_text,
    )

    messages.success(request, "Panic alert sent. Help is on the way.")

    return JsonResponse({"success": True, "alert_id": alert.id})


@login_required
def generate_booking_agreement(request, booking_id):
    """Generate and email service agreement PDF."""
    booking = get_object_or_404(Booking, id=booking_id)

    if request.user not in [booking.family.user, booking.caregiver.user]:
        messages.error(request, "Unauthorized.")
        return redirect("family_dashboard" if request.user.is_family else "caregiver_dashboard")

    pdf_buffer = generate_service_agreement_pdf(booking)

    try:
        send_service_agreement_email(booking, pdf_buffer)
        messages.success(request, "Service agreement generated and emailed to both parties.")
    except Exception as exc:
        messages.error(request, f"Error generating agreement: {exc}")

    return redirect("active_booking", booking_id=booking.id)
