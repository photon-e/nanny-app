"""Utility functions for PDF generation, geofencing, etc."""
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from io import BytesIO
import os

# Optional reportlab import for PDF generation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def generate_service_agreement_pdf(booking):
    """Generate PDF Service Agreement for booking."""
    if not REPORTLAB_AVAILABLE:
        # Fallback: Generate a simple text version
        content = f"""
Service Agreement

This Service Agreement is entered into on {timezone.now().strftime('%B %d, %Y')} between:

Family: {booking.family.user.get_full_name() or booking.family.user.username}
Caregiver: {booking.caregiver.user.get_full_name() or booking.caregiver.user.username}
Service Date: {booking.service_date or 'TBD'}
Amount: ₦{booking.amount}

IMPORTANT LEGAL NOTICE:
This platform acts solely as an agent facilitating the connection between families and caregivers.
The platform is not a party to this agreement. The family and caregiver are contracting directly
with each other. The platform assumes no liability for the services provided or any disputes
that may arise between the parties.

Terms:
1. The caregiver agrees to provide childcare services as agreed upon.
2. Payment is held in escrow until service completion.
3. Both parties agree to abide by the platform's Code of Conduct.
4. Any disputes should be reported through the platform's dispute resolution system.

Signatures:
Family: _________________________ Date: ___________
Caregiver: _______________________ Date: ___________
"""
        buffer = BytesIO()
        buffer.write(content.encode('utf-8'))
        buffer.seek(0)
        return buffer
    
    # Use reportlab if available
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor='#1e40af',
        spaceAfter=30,
    )
    
    story = []
    
    # Title
    story.append(Paragraph("Service Agreement", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Agreement content
    content = f"""
    <b>This Service Agreement</b> is entered into on {timezone.now().strftime('%B %d, %Y')} between:
    <br/><br/>
    <b>Family:</b> {booking.family.user.get_full_name() or booking.family.user.username}<br/>
    <b>Caregiver:</b> {booking.caregiver.user.get_full_name() or booking.caregiver.user.username}<br/>
    <b>Service Date:</b> {booking.service_date or 'TBD'}<br/>
    <b>Amount:</b> ₦{booking.amount}<br/><br/>
    
    <b>IMPORTANT LEGAL NOTICE:</b><br/>
    This platform acts solely as an agent facilitating the connection between families and caregivers.
    The platform is not a party to this agreement. The family and caregiver are contracting directly
    with each other. The platform assumes no liability for the services provided or any disputes
    that may arise between the parties.<br/><br/>
    
    <b>Terms:</b><br/>
    1. The caregiver agrees to provide childcare services as agreed upon.<br/>
    2. Payment is held in escrow until service completion.<br/>
    3. Both parties agree to abide by the platform's Code of Conduct.<br/>
    4. Any disputes should be reported through the platform's dispute resolution system.<br/><br/>
    
    <b>Signatures:</b><br/>
    Family: _________________________ Date: ___________<br/>
    Caregiver: _______________________ Date: ___________<br/>
    """
    
    story.append(Paragraph(content, styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer


def send_service_agreement_email(booking, pdf_buffer):
    """Email service agreement PDF to both parties."""
    from core.models import ServiceAgreement
    
    # Save PDF
    agreement, created = ServiceAgreement.objects.get_or_create(booking=booking)
    
    # Save PDF file (simplified - you'd save to FileField in production)
    pdf_filename = f'service_agreement_{booking.id}.pdf'
    pdf_path = os.path.join(settings.MEDIA_ROOT, 'service_agreements', pdf_filename)
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    
    with open(pdf_path, 'wb') as f:
        f.write(pdf_buffer.read())
    
    agreement.pdf_file.name = f'service_agreements/{pdf_filename}'
    agreement.save()
    
    # Email to family
    subject = f"Service Agreement - Booking #{booking.id}"
    message = f"""
    Dear {booking.family.user.get_full_name() or booking.family.user.username},
    
    Please find attached the Service Agreement for your booking with {booking.caregiver.user.get_full_name() or booking.caregiver.user.username}.
    
    This agreement outlines the terms and conditions of the service.
    
    Best regards,
    Nanny Platform Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [booking.family.user.email],
            fail_silently=False,
        )
        agreement.sent_to_family = True
    except Exception as e:
        print(f"Error sending email to family: {e}")
    
    # Email to caregiver
    try:
        send_mail(
            subject,
            message.replace(booking.family.user.get_full_name(), booking.caregiver.user.get_full_name()),
            settings.DEFAULT_FROM_EMAIL,
            [booking.caregiver.user.email],
            fail_silently=False,
        )
        agreement.sent_to_caregiver = True
    except Exception as e:
        print(f"Error sending email to caregiver: {e}")
    
    agreement.save()
    return agreement


def check_geofence(expected_lat, expected_lng, actual_lat, actual_lng, radius_meters=100):
    """Check if actual location is within radius of expected location."""
    from math import radians, cos, sin, asin, sqrt
    
    # Haversine formula to calculate distance
    R = 6371000  # Earth radius in meters
    
    lat1, lon1 = radians(float(expected_lat)), radians(float(expected_lng))
    lat2, lon2 = radians(float(actual_lat)), radians(float(actual_lng))
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    distance = R * c
    
    return distance <= radius_meters
