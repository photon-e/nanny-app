import json
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, BooleanField, Case, Count, Q, Value, When
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from caregivers.models import CaregiverProfile

from .forms import FamilyProfileForm
from .models import AuthorizedPickup, Booking, FamilyProfile, IncidentReport, PaymentEvent
from .payments import (
    PaymentGatewayError,
    initialize_checkout,
    validate_webhook_signature,
    verify_transaction,
)


def _get_or_create_family_profile(user):
    profile, _ = FamilyProfile.objects.get_or_create(user=user, defaults={"location": ""})
    return profile


def _apply_payment_success(booking, reference, message="Payment captured and moved to escrow"):
    if booking.status in ["released", "refunded"]:
        return False

    booking.status = "escrow"
    booking.provider_reference = reference
    booking.payment_verified_at = timezone.now()
    booking.last_payment_error = ""
    booking.save(update_fields=["status", "provider_reference", "payment_verified_at", "last_payment_error"])
    PaymentEvent.objects.create(
        booking=booking,
        provider=booking.payment_provider,
        reference=reference,
        event_type="charge.success",
        status="processed",
        message=message,
    )
    return True


def _apply_payment_failure(booking, reference, message="Payment failed"):
    if booking.status in ["released", "refunded"]:
        return False

    booking.status = "pending"
    booking.last_payment_error = message
    if reference:
        booking.provider_reference = reference
        booking.save(update_fields=["status", "last_payment_error", "provider_reference"])
    else:
        booking.save(update_fields=["status", "last_payment_error"])
    PaymentEvent.objects.create(
        booking=booking,
        provider=booking.payment_provider,
        reference=reference or booking.checkout_reference,
        event_type="charge.failed",
        status="processed",
        message=message,
    )
    return True

def _process_webhook_payload(payload):
    event_type = payload.get("event", "unknown")
    data = payload.get("data", {})
    reference = data.get("reference")

    if not reference:
        return False, "missing reference"

    booking = Booking.objects.filter(checkout_reference=reference).first()
    if not booking:
        return True, "no matching booking"

    payment_event = PaymentEvent.objects.create(
        booking=booking,
        provider=booking.payment_provider,
        reference=reference,
        event_type=event_type,
        status="received",
        payload=payload,
    )

    if event_type in ["charge.success", "payment.success"]:
        changed = _apply_payment_success(booking, reference, "Webhook payment success")
        payment_event.status = "processed" if changed else "ignored"
        payment_event.message = "Escrow updated" if changed else "Booking already finalized"
    elif event_type in ["charge.failed", "payment.failed"]:
        changed = _apply_payment_failure(booking, reference, data.get("gateway_response", "payment failed"))
        payment_event.status = "processed" if changed else "ignored"
        payment_event.message = "Failure reconciled" if changed else "Booking already finalized"
    else:
        payment_event.status = "ignored"
        payment_event.message = "Unsupported event"

    payment_event.save(update_fields=["status", "message"])
    return True, "ok"



@login_required
def family_dashboard(request):
    if not request.user.is_family:
        return redirect("/")

    profile = _get_or_create_family_profile(request.user)

    if request.method == "POST":
        form = FamilyProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("family_dashboard")
    else:
        form = FamilyProfileForm(instance=profile)

    pickups = profile.authorized_pickups.all()
    recent_bookings = profile.bookings.select_related("caregiver", "caregiver__user").all()[:5]
    incidents = profile.incidents.all()[:5]
    incident_caregivers = (
        CaregiverProfile.objects.filter(bookings__family=profile)
        .select_related("user")
        .distinct()
        .order_by("user__first_name", "user__last_name", "user__username")
    )

    return render(
        request,
        "families/dashboard.html",
        {
            "form": form,
            "profile": profile,
            "authorized_pickups": pickups,
            "recent_bookings": recent_bookings,
            "incidents": incidents,
            "incident_caregivers": incident_caregivers,
        },
    )


@login_required
def caregiver_search(request):
    """Smart search & filters for parents."""
    if not request.user.is_family:
        return redirect("/")

    profile = _get_or_create_family_profile(request.user)

    q = request.GET.get("q")
    location = request.GET.get("location")
    verification = request.GET.get("verification")  # "gold" / "standard" / None
    sort = request.GET.get("sort") or "recommended"

    caregivers = CaregiverProfile.objects.select_related("user").filter(is_available=True)

    if q:
        caregivers = caregivers.filter(
            Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) | Q(bio__icontains=q)
        )

    if location:
        caregivers = caregivers.filter(location__icontains=location)

    if verification == "gold":
        caregivers = caregivers.filter(verified=True)
    elif verification == "standard":
        caregivers = caregivers.filter(verified=False, registration_level__gte=2)

    caregivers = caregivers.annotate(
        has_id=Case(
            When(nin_document__isnull=False, then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        ),
        has_guarantors=Count("guarantors"),
        has_selfie=Case(
            When(selfie_photo__isnull=False, then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        ),
        average_rating=Avg("reviews__overall_rating", filter=Q(reviews__is_visible=True)),
        review_count=Count("reviews", filter=Q(reviews__is_visible=True), distinct=True),
    )

    sort_options = {
        "recommended": ["-verified", "-registration_level", "-review_count", "-created_at"],
        "highest_rated": ["-average_rating", "-review_count", "-verified"],
        "lowest_rate": ["hourly_rate", "-verified"],
        "most_experienced": ["-experience_years", "-verified"],
    }
    caregivers = caregivers.order_by(*sort_options.get(sort, sort_options["recommended"]))

    paginator = Paginator(caregivers, 9)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    active_filters = []
    if q:
        active_filters.append({"label": f'Keyword: "{q}"', "param": "q"})
    if location:
        active_filters.append({"label": f'Location: "{location}"', "param": "location"})
    if verification == "gold":
        active_filters.append({"label": "Gold verification", "param": "verification"})
    elif verification == "standard":
        active_filters.append({"label": "Standard verification", "param": "verification"})

    query_params = request.GET.copy()
    if "page" in query_params:
        query_params.pop("page")
    query_string = query_params.urlencode()

    return render(
        request,
        "families/caregiver_search.html",
        {
            "profile": profile,
            "caregivers": page_obj.object_list,
            "page_obj": page_obj,
            "result_count": paginator.count,
            "active_filters": active_filters,
            "query_string": query_string,
            "search_q": q or "",
            "search_location": location or "",
            "search_verification": verification or "",
            "search_sort": sort,
        },
    )


@login_required
def create_booking(request, caregiver_id):
    if not request.user.is_family:
        return redirect("/")

    profile = _get_or_create_family_profile(request.user)
    caregiver = CaregiverProfile.objects.select_related("user").get(id=caregiver_id)

    amount = caregiver.hourly_rate or Decimal("10000")
    provider = profile.default_payment_provider or "paystack"

    commission_rate = Decimal("0.15")
    agent_commission = amount * commission_rate
    caregiver_payout = amount - agent_commission

    service_start = timezone.now() + timedelta(days=1)
    service_end = service_start + timedelta(hours=8)

    booking = Booking.objects.create(
        family=profile,
        caregiver=caregiver,
        amount=amount,
        service_start=service_start,
        service_end=service_end,
        service_location_lat=Decimal("6.524400"),
        service_location_lng=Decimal("3.379200"),
        payment_provider=provider,
        status="pending",
        agent_commission=agent_commission,
        caregiver_payout=caregiver_payout,
    )

    try:
        from core.utils import generate_service_agreement_pdf, send_service_agreement_email

        pdf_buffer = generate_service_agreement_pdf(booking)
        send_service_agreement_email(booking, pdf_buffer)
    except Exception as exc:  # noqa: BLE001
        print(f"Error generating agreement: {exc}")

    return redirect("start_booking_checkout", booking_id=booking.id)


@login_required
def start_booking_checkout(request, booking_id):
    booking = get_object_or_404(Booking.objects.select_related("family__user"), id=booking_id)
    if request.user != booking.family.user:
        messages.error(request, "Unauthorized.")
        return redirect("/")

    if booking.status == "released":
        messages.info(request, "This booking has already been completed.")
        return redirect("active_booking", booking_id=booking.id)

    try:
        session = initialize_checkout(request, booking)
    except PaymentGatewayError as exc:
        booking.last_payment_error = str(exc)
        booking.save(update_fields=["last_payment_error"])
        messages.error(request, "Unable to initialize checkout right now. Please try again.")
        return redirect("family_dashboard")

    booking.checkout_reference = session.reference
    booking.last_payment_error = ""
    booking.save(update_fields=["checkout_reference", "last_payment_error"])

    PaymentEvent.objects.create(
        booking=booking,
        provider=booking.payment_provider,
        reference=session.reference,
        event_type="checkout.initialized",
        status="processed",
        message="Checkout session started",
    )

    return redirect(session.checkout_url)


@require_GET
@login_required
def payment_return(request):
    reference = request.GET.get("reference", "")
    if not reference:
        messages.error(request, "Missing payment reference.")
        return redirect("family_dashboard")

    booking = get_object_or_404(Booking, checkout_reference=reference)
    if request.user != booking.family.user:
        messages.error(request, "Unauthorized.")
        return redirect("/")

    try:
        verification = verify_transaction(reference, booking.payment_provider)
    except PaymentGatewayError:
        messages.error(request, "We could not verify this payment yet. Please check back shortly.")
        return redirect("active_booking", booking_id=booking.id)

    if verification["status"]:
        _apply_payment_success(booking, verification["reference"], verification.get("gateway_response", "verified"))
        messages.success(request, "Payment confirmed and held in escrow.")
    else:
        _apply_payment_failure(booking, verification.get("reference", reference), verification.get("gateway_response", "failed"))
        messages.error(request, "Payment was not successful. Please try again.")

    return redirect("active_booking", booking_id=booking.id)


@csrf_exempt
@require_http_methods(["POST"])
def payment_webhook(request):
    signature = request.headers.get("X-Paystack-Signature", "")
    raw_body = request.body

    if not validate_webhook_signature(raw_body, signature):
        return HttpResponse("invalid signature", status=400)

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponse("invalid payload", status=400)

    processed, message = _process_webhook_payload(payload)
    if not processed:
        return HttpResponse(message, status=400)
    return HttpResponse("ok", status=200)



@login_required
@require_GET
def mock_checkout(request, booking_id):
    booking = get_object_or_404(Booking.objects.select_related("family__user"), id=booking_id)
    if request.user != booking.family.user:
        messages.error(request, "Unauthorized.")
        return redirect("/")

    action = request.GET.get("action")
    reference = request.GET.get("reference") or booking.checkout_reference
    if not action:
        return render(request, "families/mock_checkout.html", {"booking": booking, "reference": reference})

    event = "charge.success" if action == "success" else "charge.failed"
    payload = {"event": event, "data": {"reference": reference, "gateway_response": "mock"}}
    _process_webhook_payload(payload)
    return redirect(f"{reverse('payment_return')}?reference={reference}")


@login_required
@staff_member_required
@require_http_methods(["POST"])
def release_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    if booking.status != "escrow":
        messages.error(request, "Booking must be in escrow before release.")
        return redirect("active_booking", booking_id=booking.id)

    booking.status = "released"
    booking.save(update_fields=["status"])
    PaymentEvent.objects.create(
        booking=booking,
        provider=booking.payment_provider,
        reference=booking.provider_reference,
        event_type="escrow.released",
        status="processed",
        message="Released by staff",
    )
    messages.success(request, "Escrow released to caregiver.")
    return redirect("active_booking", booking_id=booking.id)


@login_required
@staff_member_required
@require_http_methods(["POST"])
def refund_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    if booking.status not in ["pending", "escrow"]:
        messages.error(request, "Only pending or escrow bookings can be refunded.")
        return redirect("active_booking", booking_id=booking.id)

    booking.status = "refunded"
    booking.last_payment_error = "Refunded by staff"
    booking.save(update_fields=["status", "last_payment_error"])
    PaymentEvent.objects.create(
        booking=booking,
        provider=booking.payment_provider,
        reference=booking.provider_reference or booking.checkout_reference,
        event_type="payment.refunded",
        status="processed",
        message="Refunded by staff",
    )
    messages.success(request, "Booking refunded.")
    return redirect("active_booking", booking_id=booking.id)


@login_required
def add_authorized_pickup(request):
    if not request.user.is_family:
        return redirect("/")

    profile = _get_or_create_family_profile(request.user)

    if request.method == "POST":
        full_name = request.POST.get("full_name")
        relationship = request.POST.get("relationship")
        photo = request.FILES.get("photo")

        if not full_name:
            messages.error(request, "Full name is required.")
        else:
            AuthorizedPickup.objects.create(
                family=profile,
                full_name=full_name,
                relationship=relationship or "",
                photo=photo,
            )
            messages.success(request, "Authorized pickup added.")

    return redirect("family_dashboard")


@login_required
def report_incident(request):
    """Digital incident log button."""
    if not request.user.is_family:
        return redirect("/")

    profile = _get_or_create_family_profile(request.user)

    if request.method == "POST":
        incident_type = request.POST.get("incident_type")
        caregiver_id = request.POST.get("caregiver_id")
        description = request.POST.get("description", "")

        caregiver = None
        if caregiver_id:
            try:
                caregiver = CaregiverProfile.objects.filter(bookings__family=profile).distinct().get(id=caregiver_id)
            except CaregiverProfile.DoesNotExist:
                messages.error(request, "Please select a caregiver from your booking history.")
                return redirect("family_dashboard")

        if incident_type not in dict(IncidentReport.INCIDENT_CHOICES):
            messages.error(request, "Please select a valid incident type.")
        else:
            IncidentReport.objects.create(
                family=profile,
                caregiver=caregiver,
                incident_type=incident_type,
                description=description,
            )
            messages.success(request, "Incident reported. Our team will review it.")

    return redirect("family_dashboard")
