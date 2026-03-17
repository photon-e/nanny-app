from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.family_dashboard, name="family_dashboard"),
    path("caregivers/", views.caregiver_search, name="caregiver_search"),
    path("book/<int:caregiver_id>/", views.create_booking, name="create_booking"),
    path("booking/<int:booking_id>/checkout/", views.start_booking_checkout, name="start_booking_checkout"),
    path("payments/return/", views.payment_return, name="payment_return"),
    path("payments/webhook/", views.payment_webhook, name="payment_webhook"),
    path("payments/mock/<int:booking_id>/", views.mock_checkout, name="mock_checkout"),
    path("booking/<int:booking_id>/release/", views.release_booking, name="release_booking"),
    path("booking/<int:booking_id>/refund/", views.refund_booking, name="refund_booking"),
    path("authorized-pickup/add/", views.add_authorized_pickup, name="add_authorized_pickup"),
    path("incident/report/", views.report_incident, name="report_incident"),
]
