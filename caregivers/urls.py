from django.urls import path
from . import views

urlpatterns = [
    path('', views.caregiver_list, name='caregiver_list'),
    path('dashboard/', views.caregiver_dashboard, name='caregiver_dashboard'),
    path('<int:pk>/', views.caregiver_detail, name='caregiver_detail'),
    
    # Tiered Registration URLs
    path('registration/level1/', views.caregiver_registration_level1, name='caregiver_registration_level1'),
    path('registration/level2/', views.caregiver_registration_level2, name='caregiver_registration_level2'),
    path('registration/level3/', views.caregiver_registration_level3, name='caregiver_registration_level3'),
    
    # Code of Conduct
    path('code-of-conduct/', views.code_of_conduct, name='code_of_conduct'),
    
    # Training Modules
    path('training/', views.training_modules, name='training_modules'),
    path('training/<int:module_id>/', views.training_module_detail, name='training_module_detail'),
    
    # Availability Toggle
    path('toggle-availability/', views.toggle_availability, name='toggle_availability'),
    
    # Earnings Wallet
    path('earnings/', views.earnings_wallet, name='earnings_wallet'),
]

