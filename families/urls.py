from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.family_dashboard, name="family_dashboard"),
    path("caregivers/", views.caregiver_search, name="caregiver_search"),
    path("book/<int:caregiver_id>/", views.create_booking, name="create_booking"),
    path("authorized-pickup/add/", views.add_authorized_pickup, name="add_authorized_pickup"),
    path("incident/report/", views.report_incident, name="report_incident"),
]
