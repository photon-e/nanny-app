from django.shortcuts import get_object_or_404, redirect, render
from .models import (
    CaregiverProfile, Guarantor, CodeOfConductSignature, 
    TrainingModule, TrainingQuiz, TrainingCompletion, EarningsWallet
)

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum
from .forms import (
    CaregiverProfileForm, Level1RegistrationForm, Level2RegistrationForm, 
    Level3RegistrationForm, CodeOfConductForm, TrainingQuizForm
)


from django.db.models import Avg, Count, Q
from decimal import Decimal, InvalidOperation

from families.models import Booking, CaregiverReview
from core.models import MonitoredMessage


def _parse_positive_int(value):
    if value in (None, ""):
        return None
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _parse_decimal(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, TypeError):
        return None


def caregiver_list(request):
    q = (request.GET.get("q") or "").strip()
    caregivers = CaregiverProfile.objects.select_related("user").annotate(
        average_rating=Avg("reviews__overall_rating", filter=Q(reviews__is_visible=True)),
        review_count=Count("reviews", filter=Q(reviews__is_visible=True), distinct=True),
    )

    q = (request.GET.get("q") or "").strip()
    location = (request.GET.get("location") or "").strip()
    min_exp = _parse_positive_int(request.GET.get("min_exp"))
    max_rate = _parse_decimal(request.GET.get("max_rate"))

    if q:
        caregivers = caregivers.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(bio__icontains=q)
        )

    if location:
        caregivers = caregivers.filter(location__icontains=location)

    if min_exp is not None:
        caregivers = caregivers.filter(experience_years__gte=min_exp)

    if max_rate is not None:
        caregivers = caregivers.filter(hourly_rate__lte=max_rate)

    return render(
        request,
        "caregivers/profile_list.html",
        {
            "caregivers": caregivers,
            "search_q": q,
            "search_location": location,
            "search_min_exp": "" if min_exp is None else str(min_exp),
            "search_max_rate": "" if max_rate is None else str(max_rate.quantize(Decimal("1")) if max_rate == max_rate.to_integral_value() else max_rate),
        },
    )


def caregiver_detail(request, pk):
    caregiver = get_object_or_404(CaregiverProfile, pk=pk)
    visible_reviews = CaregiverReview.objects.filter(caregiver=caregiver, is_visible=True).select_related(
        "family__user"
    )
    rating_summary = visible_reviews.aggregate(avg_rating=Avg("overall_rating"), review_count=Count("id"))

    return render(request, "caregivers/profile_detail.html", {
        "caregiver": caregiver,
        "reviews": visible_reviews[:10],
        "average_rating": rating_summary["avg_rating"],
        "review_count": rating_summary["review_count"],
    })

@login_required
def caregiver_dashboard(request):
    if not request.user.is_caregiver:
        return redirect('/')

    # Get profile
    profile, created = CaregiverProfile.objects.get_or_create(user=request.user)
    
    # Check registration status and redirect if incomplete
    if profile.registration_level < 1 or not profile.can_proceed_to_level_2():
        messages.info(request, 'Please complete Level 1 registration to access your dashboard.')
        return redirect('caregiver_registration_level1')
    elif profile.registration_level < 2 or not profile.can_proceed_to_level_3():
        messages.info(request, 'Please complete Level 2 registration to access your dashboard.')
        return redirect('caregiver_registration_level2')
    elif profile.registration_level < 3 or profile.guarantors.count() < 2:
        messages.info(request, 'Please complete Level 3 registration to access your dashboard.')
        return redirect('caregiver_registration_level3')
    
    # Check if code of conduct is signed - mandatory before seeing jobs
    if not profile.code_of_conduct_signed:
        messages.warning(request, 'You must sign the Code of Conduct before accessing jobs.')
        return redirect('code_of_conduct')

    if request.method == "POST":
        form = CaregiverProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            # Refresh profile from DB after saving to get the updated image
            profile.refresh_from_db()
            return redirect('caregiver_dashboard')  # reload page to show image
    else:
        form = CaregiverProfileForm(instance=profile)

    active_bookings = (
        Booking.objects.select_related("family__user")
        .filter(caregiver=profile)
        .order_by("-created_at")
    )
    recent_bookings = active_bookings[:5]

    assigned_families = []
    seen_family_ids = set()
    for booking in active_bookings:
        family = booking.family
        if family.id in seen_family_ids:
            continue
        seen_family_ids.add(family.id)
        assigned_families.append(
            {
                "id": family.id,
                "full_name": family.user.get_full_name() or family.user.username,
                "location": family.location,
            }
        )

    recent_messages = (
        MonitoredMessage.objects.select_related("sender", "booking")
        .filter(booking__caregiver=profile)
        .order_by("-created_at")[:5]
    )

    context = {
        'profile': profile,
        'form': form,
        'assigned_families': assigned_families,
        'messages': recent_messages,
        'recent_bookings': recent_bookings,
    }

    return render(request, "caregivers/dashboard.html", context)


@login_required
def caregiver_registration_level1(request):
    """Level 1 Registration: Basic Information"""
    if not request.user.is_caregiver:
        return redirect('/')
    
    profile, created = CaregiverProfile.objects.get_or_create(user=request.user)
    
    # If already completed Level 1, redirect to next level
    if profile.registration_level > 1:
        return redirect('caregiver_registration_level2')
    
    if request.method == 'POST':
        form = Level1RegistrationForm(request.POST)
        if form.is_valid():
            # Update user name
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.save()
            
            # Update profile
            profile.phone = form.cleaned_data['phone']
            profile.date_of_birth = form.cleaned_data['date_of_birth']
            profile.location = form.cleaned_data['location']
            profile.registration_level = 1
            profile.save()
            
            messages.success(request, 'Level 1 registration completed! Please proceed to Level 2.')
            return redirect('caregiver_registration_level2')
    else:
        # Pre-fill form with existing data
        initial_data = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'phone': profile.phone,
            'date_of_birth': profile.date_of_birth,
            'location': profile.location,
        }
        form = Level1RegistrationForm(initial=initial_data)
    
    return render(request, 'caregivers/registration_level1.html', {
        'form': form,
        'profile': profile,
    })


@login_required
def caregiver_registration_level2(request):
    """Level 2 Registration: Identity Verification"""
    if not request.user.is_caregiver:
        return redirect('/')
    
    profile, created = CaregiverProfile.objects.get_or_create(user=request.user)
    
    # Check if Level 1 is completed
    if not profile.can_proceed_to_level_2():
        messages.warning(request, 'Please complete Level 1 registration first.')
        return redirect('caregiver_registration_level1')
    
    # If already completed Level 2, redirect to next level
    if profile.registration_level > 2:
        return redirect('caregiver_registration_level3')
    
    if request.method == 'POST':
        form = Level2RegistrationForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            profile.registration_level = 2
            profile.save()
            messages.success(request, 'Level 2 registration completed! Please proceed to Level 3.')
            return redirect('caregiver_registration_level3')
    else:
        form = Level2RegistrationForm(instance=profile)
    
    return render(request, 'caregivers/registration_level2.html', {
        'form': form,
        'profile': profile,
    })


@login_required
def caregiver_registration_level3(request):
    """Level 3 Registration: Guarantors"""
    if not request.user.is_caregiver:
        return redirect('/')
    
    profile, created = CaregiverProfile.objects.get_or_create(user=request.user)
    
    # Check if Level 2 is completed
    if not profile.can_proceed_to_level_3():
        messages.warning(request, 'Please complete Level 2 registration first.')
        return redirect('caregiver_registration_level2')
    
    # Check if already has 2 guarantors
    existing_guarantors = profile.guarantors.all()
    if existing_guarantors.count() >= 2:
        messages.info(request, 'You have already completed Level 3 registration.')
        return redirect('caregiver_dashboard')
    
    if request.method == 'POST':
        form = Level3RegistrationForm(request.POST)
        if form.is_valid():
            # Create guarantor 1
            guarantor1 = Guarantor.objects.create(
                caregiver=profile,
                full_name=form.cleaned_data['guarantor1_name'],
                nin=form.cleaned_data['guarantor1_nin'],
                phone=form.cleaned_data['guarantor1_phone'],
                phone_verified=False  # Would need phone verification service
            )
            
            # Create guarantor 2
            guarantor2 = Guarantor.objects.create(
                caregiver=profile,
                full_name=form.cleaned_data['guarantor2_name'],
                nin=form.cleaned_data['guarantor2_nin'],
                phone=form.cleaned_data['guarantor2_phone'],
                phone_verified=False  # Would need phone verification service
            )
            
            profile.registration_level = 3
            profile.save()
            
            messages.success(request, 'Congratulations! You have completed all registration levels.')
            return redirect('caregiver_dashboard')
    else:
        form = Level3RegistrationForm()
    
    return render(request, 'caregivers/registration_level3.html', {
        'form': form,
        'profile': profile,
    })


@login_required
def code_of_conduct(request):
    """Code of Conduct screen - mandatory before seeing jobs"""
    if not request.user.is_caregiver:
        return redirect('/')
    
    profile, created = CaregiverProfile.objects.get_or_create(user=request.user)
    
    # If already signed, redirect to dashboard
    if profile.code_of_conduct_signed:
        messages.info(request, 'You have already signed the Code of Conduct.')
        return redirect('caregiver_dashboard')
    
    code_of_conduct_text = """
    <h2 class="text-2xl font-bold mb-4">Digital Code of Conduct</h2>
    
    <p class="mb-4">As a caregiver on our platform, you agree to abide by the following code of conduct:</p>
    
    <div class="space-y-4 mb-6">
        <div class="border-l-4 border-red-500 pl-4">
            <h3 class="font-bold text-lg mb-2">1. No Social Media</h3>
            <p>You are strictly prohibited from sharing any information about the families you work with on social media platforms. This includes photos, names, locations, or any details about the children or families.</p>
        </div>
        
        <div class="border-l-4 border-red-500 pl-4">
            <h3 class="font-bold text-lg mb-2">2. No Spiritualism</h3>
            <p>You must not engage in or promote any spiritual, religious, or superstitious practices while caring for children. Maintain a professional, secular approach to childcare.</p>
        </div>
        
        <div class="border-l-4 border-red-500 pl-4">
            <h3 class="font-bold text-lg mb-2">3. No Visitors</h3>
            <p>You are not permitted to have visitors, friends, or family members at the family's home during your caregiving hours. Only authorized individuals should be present.</p>
        </div>
    </div>
    
    <p class="mb-4"><strong>Violation of any of these rules will result in immediate termination and may result in legal action.</strong></p>
    
    <p class="text-sm text-gray-600">By signing below, you acknowledge that you have read, understood, and agree to abide by this Code of Conduct.</p>
    """
    
    if request.method == 'POST':
        form = CodeOfConductForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['agree']:
                # Create signature record
                CodeOfConductSignature.objects.create(
                    caregiver=profile,
                    ip_address=get_client_ip(request)
                )
                profile.code_of_conduct_signed = True
                profile.save()
                
                messages.success(request, 'Code of Conduct signed successfully!')
                return redirect('caregiver_dashboard')
            else:
                messages.error(request, 'You must agree to the Code of Conduct to continue.')
    else:
        form = CodeOfConductForm()
    
    return render(request, 'caregivers/code_of_conduct.html', {
        'form': form,
        'code_of_conduct_text': code_of_conduct_text,
        'profile': profile,
    })


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@login_required
def training_modules(request):
    """List of training modules"""
    if not request.user.is_caregiver:
        return redirect('/')
    
    profile, created = CaregiverProfile.objects.get_or_create(user=request.user)
    modules = TrainingModule.objects.filter(is_active=True)
    
    # Get completion status for each module
    completions = {c.module_id: c for c in TrainingCompletion.objects.filter(caregiver=profile)}
    
    for module in modules:
        module.completion = completions.get(module.id)
        module.is_completed = module.completion and module.completion.passed
    
    return render(request, 'caregivers/training_modules.html', {
        'modules': modules,
        'profile': profile,
    })


@login_required
def training_module_detail(request, module_id):
    """Training module detail and quiz"""
    if not request.user.is_caregiver:
        return redirect('/')
    
    profile, created = CaregiverProfile.objects.get_or_create(user=request.user)
    module = get_object_or_404(TrainingModule, id=module_id, is_active=True)
    
    # Check if already passed
    completion = TrainingCompletion.objects.filter(caregiver=profile, module=module).first()
    if completion and completion.passed:
        messages.info(request, 'You have already passed this training module.')
        return redirect('training_modules')
    
    questions = TrainingQuiz.objects.filter(module=module).order_by('order')
    
    if request.method == 'POST':
        form = TrainingQuizForm(request.POST, questions=questions)
        if form.is_valid():
            # Grade the quiz
            correct = 0
            total = len(questions)
            
            for question in questions:
                answer_key = f'question_{question.id}'
                user_answer = form.cleaned_data.get(answer_key)
                if user_answer == question.correct_answer:
                    correct += 1
            
            score = int((correct / total) * 100) if total > 0 else 0
            passed = score >= 70  # 70% to pass
            
            # Save completion
            completion, created = TrainingCompletion.objects.update_or_create(
                caregiver=profile,
                module=module,
                defaults={
                    'passed': passed,
                    'score': score,
                    'total_questions': total,
                }
            )
            
            # Update verified status if all required modules passed
            if passed:
                # Check if this is the required training (First Aid and Emergency Protocols)
                required_modules = TrainingModule.objects.filter(
                    is_active=True,
                    title__icontains='First Aid'
                ) | TrainingModule.objects.filter(
                    is_active=True,
                    title__icontains='Emergency'
                )
                
                all_required_passed = all(
                    TrainingCompletion.objects.filter(
                        caregiver=profile,
                        module=mod,
                        passed=True
                    ).exists()
                    for mod in required_modules
                )
                
                if all_required_passed:
                    profile.verified = True
                    profile.save()
                    messages.success(request, f'Congratulations! You passed the quiz with {score}%. You are now verified!')
                else:
                    messages.success(request, f'You passed the quiz with {score}%! Complete all required modules to get verified.')
            else:
                messages.error(request, f'You scored {score}%. You need 70% to pass. Please try again.')
            
            return redirect('training_modules')
    else:
        form = TrainingQuizForm(questions=questions)
    
    return render(request, 'caregivers/training_module_detail.html', {
        'module': module,
        'form': form,
        'questions': questions,
        'profile': profile,
    })


@login_required
def toggle_availability(request):
    """Toggle caregiver availability"""
    if not request.user.is_caregiver:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        profile, created = CaregiverProfile.objects.get_or_create(user=request.user)
        profile.is_available = not profile.is_available
        profile.save()
        
        return JsonResponse({
            'success': True,
            'is_available': profile.is_available
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def earnings_wallet(request):
    """Earnings wallet view"""
    if not request.user.is_caregiver:
        return redirect('/')
    
    profile, created = CaregiverProfile.objects.get_or_create(user=request.user)
    earnings = EarningsWallet.objects.filter(caregiver=profile)
    
    # Calculate totals
    total_earnings = earnings.aggregate(total=Sum('amount'))['total'] or 0
    pending_earnings = earnings.filter(payout_status='pending').aggregate(total=Sum('amount'))['total'] or 0
    completed_earnings = earnings.filter(payout_status='completed').aggregate(total=Sum('amount'))['total'] or 0
    
    return render(request, 'caregivers/earnings_wallet.html', {
        'earnings': earnings,
        'total_earnings': total_earnings,
        'pending_earnings': pending_earnings,
        'completed_earnings': completed_earnings,
        'profile': profile,
    })
