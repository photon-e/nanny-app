from django.shortcuts import render, redirect
from .forms import CaregiverSignupForm, FamilySignupForm

def family_signup(request):
    if request.method == 'POST':
        form = FamilySignupForm(request.POST)
        if form.is_valid():
            user = form.save(request)
            # Auto-login user
            from django.contrib.auth import login
            login(request, user)
            return redirect('family_dashboard')
    else:
        form = FamilySignupForm()

    return render(request, 'accounts/signup.html', {'form': form, 'role': 'Family'})


def caregiver_signup(request):
    if request.method == 'POST':
        form = CaregiverSignupForm(request.POST)
        if form.is_valid():
            user = form.save(request)
            from django.contrib.auth import login
            login(request, user)
            # Redirect to Level 1 registration instead of dashboard
            return redirect('caregiver_registration_level1')
    else:
        form = CaregiverSignupForm()

    return render(request, 'accounts/signup.html', {'form': form, 'role': 'Caregiver'})

