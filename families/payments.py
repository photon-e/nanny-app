import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass
from urllib import error, request

from django.conf import settings
from django.urls import reverse


@dataclass
class CheckoutSession:
    reference: str
    checkout_url: str


class PaymentGatewayError(Exception):
    pass


class UnsupportedPaymentProvider(PaymentGatewayError):
    pass


def _payment_mode():
    return getattr(settings, "PAYMENT_GATEWAY_MODE", "mock").lower()


def _paystack_secret_key():
    return getattr(settings, "PAYSTACK_SECRET_KEY", "")


def _paystack_webhook_secret():
    return getattr(settings, "PAYSTACK_WEBHOOK_SECRET", _paystack_secret_key())


def _paystack_base_url():
    return getattr(settings, "PAYSTACK_BASE_URL", "https://api.paystack.co")


def generate_reference(prefix="kin"):
    return f"{prefix}_{uuid.uuid4().hex[:20]}"


def initialize_checkout(request_obj, booking):
    mode = _payment_mode()
    if mode == "mock":
        reference = generate_reference(booking.payment_provider)
        checkout_url = request_obj.build_absolute_uri(
            reverse("mock_checkout", args=[booking.id])
        ) + f"?reference={reference}"
        return CheckoutSession(reference=reference, checkout_url=checkout_url)

    if booking.payment_provider != "paystack":
        raise UnsupportedPaymentProvider(
            f"Live mode currently supports only paystack, got {booking.payment_provider}."
        )

    callback_url = request_obj.build_absolute_uri(reverse("payment_return"))
    payload = {
        "email": booking.family.user.email,
        "amount": int(booking.amount * 100),
        "reference": generate_reference("paystack"),
        "callback_url": callback_url,
        "metadata": {
            "booking_id": booking.id,
            "family_id": booking.family_id,
            "caregiver_id": booking.caregiver_id,
        },
    }
    body = json.dumps(payload).encode("utf-8")

    req = request.Request(
        url=f"{_paystack_base_url().rstrip('/')}/transaction/initialize",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {_paystack_secret_key()}",
            "Content-Type": "application/json",
        },
    )

    try:
        with request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (error.HTTPError, error.URLError, TimeoutError) as exc:
        raise PaymentGatewayError("Unable to initialize payment with provider") from exc

    if not data.get("status"):
        raise PaymentGatewayError(data.get("message", "Provider rejected checkout init"))

    provider_data = data.get("data", {})
    return CheckoutSession(
        reference=provider_data.get("reference", payload["reference"]),
        checkout_url=provider_data.get("authorization_url", callback_url),
    )


def verify_transaction(reference, provider):
    if _payment_mode() == "mock":
        from .models import PaymentEvent

        last_event = PaymentEvent.objects.filter(reference=reference).order_by("-created_at").first()
        if last_event and last_event.event_type in ["charge.failed", "payment.failed"]:
            return {"status": False, "reference": reference, "gateway_response": "mock_failed"}
        return {"status": True, "reference": reference, "gateway_response": "mock_verified"}

    if provider != "paystack":
        raise UnsupportedPaymentProvider(f"Verification not implemented for provider: {provider}")

    req = request.Request(
        url=f"{_paystack_base_url().rstrip('/')}/transaction/verify/{reference}",
        method="GET",
        headers={"Authorization": f"Bearer {_paystack_secret_key()}"},
    )

    try:
        with request.urlopen(req, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (error.HTTPError, error.URLError, TimeoutError) as exc:
        raise PaymentGatewayError("Unable to verify payment with provider") from exc

    if not payload.get("status"):
        return {"status": False, "reference": reference, "gateway_response": payload.get("message", "not_verified")}

    data = payload.get("data", {})
    return {
        "status": data.get("status") == "success",
        "reference": data.get("reference", reference),
        "gateway_response": data.get("gateway_response", data.get("status", "unknown")),
    }


def validate_webhook_signature(raw_body, signature):
    if not signature:
        return False

    mode = _payment_mode()
    if mode == "mock":
        secret = getattr(settings, "MOCK_WEBHOOK_SECRET", "mock-webhook-secret")
    else:
        secret = _paystack_webhook_secret()

    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)


def build_webhook_signature(payload):
    secret = getattr(settings, "MOCK_WEBHOOK_SECRET", "mock-webhook-secret")
    raw_body = json.dumps(payload).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()
    return raw_body, signature
