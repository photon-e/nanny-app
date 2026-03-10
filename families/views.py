from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.contrib import messages
from django.db.models import Count, Q, Case, When, Value, BooleanField
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .forms import FamilyProfileForm
from .models import AuthorizedPickup, Booking, FamilyProfile, IncidentReport
from caregivers.models import CaregiverProfile


def _get_or_create_family_profile(user):
    profile, _ = FamilyProfile.objects.get_or_create(user=user, defaults={"location": ""})
    return profile


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

    return render(
        request,
        "families/dashboard.html",
        {
            "form": form,
            "profile": profile,
            "authorized_pickups": pickups,
            "recent_bookings": recent_bookings,
            "incidents": incidents,
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

    caregivers = CaregiverProfile.objects.select_related("user").filter(is_available=True)

    if q:
        caregivers = caregivers.filter(
            Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(bio__icontains=q)
        )

    if location:
        caregivers = caregivers.filter(location__icontains=location)

    # Map verification levels:
    # - Gold: verified flag True
    # - Standard: not verified but completed Level 2
    if verification == "gold":
        caregivers = caregivers.filter(verified=True)
    elif verification == "standard":
        caregivers = caregivers.filter(verified=False, registration_level__gte=2)

    # Annotate trust score (simple flags derived from fields; no sensitive IDs)
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
    )

    return render(
        request,
        "families/caregiver_search.html",
        {
            "profile": profile,
            "caregivers": caregivers,
            "search_q": q or "",
            "search_location": location or "",
            "search_verification": verification or "",
        },
    )


@login_required
def create_booking(request, caregiver_id):
    """Create a basic booking record before redirecting to payment gateway."""
    if not request.user.is_family:
        return redirect("/")

    profile = _get_or_create_family_profile(request.user)

    caregiver = CaregiverProfile.objects.select_related("user").get(id=caregiver_id)

    # For now, use a simple fixed amount and provider; you can plug in actual amounts later
    amount = 10000  # e.g. 10000 NGN placeholder
    provider = profile.default_payment_provider or "paystack"

    # Calculate commission (15%)
    commission_rate = Decimal('0.15')
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
    
    # Auto-generate service agreement PDF (works with or without reportlab)
    try:
        from core.utils import generate_service_agreement_pdf, send_service_agreement_email
        pdf_buffer = generate_service_agreement_pdf(booking)
        send_service_agreement_email(booking, pdf_buffer)
    except Exception as e:
        # Log error but don't fail booking
        print(f"Error generating agreement: {e}")

    messages.info(
        request,
        "Booking created. Open the active booking workspace to track status, check-ins, and monitored chat.",
    )
    return redirect("family_dashboard")


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
                caregiver = CaregiverProfile.objects.get(id=caregiver_id)
            except CaregiverProfile.DoesNotExist:
                caregiver = None

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

