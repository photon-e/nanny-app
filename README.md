# Kinshields

Kinshields is a comprehensive nanny/caregiver matching platform with tiered registration, verification, escrow payments, and admin management features.

## Features

### For Caregivers
- **Tiered Registration System** (3 levels):
  - Level 1: Basic info (name, phone, age, location)
  - Level 2: Identity verification (NIN upload, live selfie)
  - Level 3: Guarantors (2 guarantors with NINs and verified phones)
- **Code of Conduct**: Mandatory e-signature before accessing jobs
- **Training Modules**: First Aid and Emergency Protocols with quizzes (70% pass rate)
- **Verification Badge**: Earned after completing all required training
- **Availability Toggle**: Control visibility to parents
- **Earnings Wallet**: Track earnings and payout status

### For Families/Parents
- **Smart Search & Filters**: Filter by location, verification level (Gold/Standard)
- **Trust Scorecard**: See verification status without sensitive data exposure
- **Secure Booking & Escrow**: Book caregivers with payment held in escrow
- **Authorized Pick-up List**: Manage trusted people who can pick up children
- **Digital Incident Log**: Report late arrivals, theft suspicion, or misconduct

### Admin Dashboard
- **Verification Queue**: Review and approve new caregivers (after calling guarantors)
- **Dispute Management**: Handle reported incidents, freeze payouts, ban accounts
- **Blacklist Manager**: Prevent banned caregivers from re-registering
- **Commission Tracker**: Auto-calculate 15% agent fee and caregiver payouts
- **Panic Alert Log**: Real-time SOS/Emergency notifications

### Invisible Features (Liability Protection)
- **Geofencing**: GPS check-in verification at parent's location
- **Monitored Chat**: All communication stays in-app with auto-flagging
- **PDF Service Agreement**: Auto-generated contracts emailed to both parties

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd nanny
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

**Note:** `reportlab` is optional. The app works without it, but PDF generation will use a text format instead of PDF. To enable full PDF generation:
```bash
pip install reportlab
```

4. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

5. Create superuser:
```bash
python manage.py createsuperuser
```

6. Run server:
```bash
python manage.py runserver
```

## Configuration

### Email Settings (for PDF agreements)
Update `nanny/settings.py`:
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-password'
DEFAULT_FROM_EMAIL = 'your-email@gmail.com'
```

### Payment Gateways
The booking flow now supports checkout initialization, webhook verification, reconciliation, and escrow transitions:
- Checkout init endpoint: `/families/booking/<booking_id>/checkout/`
- Return/callback endpoint: `/families/payments/return/`
- Webhook endpoint (HMAC SHA-512): `/families/payments/webhook/`

Environment settings:
```bash
PAYMENT_GATEWAY_MODE=mock  # use `live` for provider API calls
PAYSTACK_SECRET_KEY=...
PAYSTACK_WEBHOOK_SECRET=...
PAYSTACK_BASE_URL=https://api.paystack.co
MOCK_WEBHOOK_SECRET=mock-webhook-secret
```

In mock mode, `/families/payments/mock/<booking_id>/` simulates success/failure callbacks to validate pending → escrow → released/refunded flows.

## Database

The project uses SQLite by default. For production, update `settings.py` to use PostgreSQL:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'nanny_db',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## Admin Access

Access the admin panel at `/admin/` with your superuser credentials.

Key admin features:
- `/admin/caregivers/caregiverprofile/` - Verification Queue
- `/admin/core/dispute/` - Dispute Management
- `/admin/core/blacklist/` - Blacklist Manager
- `/admin/families/booking/` - Commission Tracker
- `/admin/core/panicalert/` - Panic Alerts

## Project Structure

```
nanny/
├── accounts/          # User authentication & signup
├── caregivers/         # Caregiver models, views, registration
├── families/          # Family models, booking, search
├── core/              # Admin features, geofencing, PDF generation
├── messaging/         # In-app messaging system
├── templates/         # HTML templates
└── nanny/             # Django settings & URLs
```

## License

This project is for demonstration purposes.
