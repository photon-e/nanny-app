from django.urls import path
from .views import caregiver_signup, family_signup
from allauth.account.views import LoginView

urlpatterns = [
    # Signup pages
    path('caregiver/', caregiver_signup, name='caregiver_signup'),
    path('family/', family_signup, name='family_signup'),

    # Optional: override login template if needed
    path('login/', LoginView.as_view(template_name='accounts/login.html'), name='account_login'),
]
