import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal

import requests
from django.conf import settings


logger = logging.getLogger(__name__)


class PaymentGatewayError(Exception):
    pass


@dataclass(frozen=True)
class PaymentGatewayResult:
    provider_reference: str
    raw_response: dict


class MockPaymentGatewayClient:
    def __init__(self, gateway_url=None, timeout_seconds=None):
        self.gateway_url = gateway_url if gateway_url is not None else settings.MOCK_PAYMENT_GATEWAY_URL
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.MOCK_PAYMENT_TIMEOUT_SECONDS
        )

    def create_payment(self, booking, amount):
        payload = {
            "booking_id": booking.id,
            "parent_email": booking.parent.email,
            "lsa_email": booking.lsa.email,
            "amount": str(amount),
            "currency": "AED",
        }

        if not self.gateway_url:
            provider_reference = f"mock_{uuid.uuid4().hex}"
            logger.info(
                "Using local mock payment response for booking_id=%s",
                booking.id,
            )
            return PaymentGatewayResult(
                provider_reference=provider_reference,
                raw_response={
                    "mode": "local_mock",
                    "provider_reference": provider_reference,
                    "payload": payload,
                },
            )

        try:
            response = requests.post(
                self.gateway_url,
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            response_data = response.json()
        except requests.RequestException as exc:
            logger.exception(
                "Payment gateway request failed for booking_id=%s",
                booking.id,
            )
            raise PaymentGatewayError("Payment gateway request failed.") from exc
        except ValueError as exc:
            logger.exception(
                "Payment gateway returned invalid JSON for booking_id=%s",
                booking.id,
            )
            raise PaymentGatewayError("Payment gateway returned invalid JSON.") from exc

        provider_reference = response_data.get("provider_reference")
        if not provider_reference:
            raise PaymentGatewayError("Payment gateway response missing provider_reference.")

        return PaymentGatewayResult(
            provider_reference=provider_reference,
            raw_response=response_data,
        )


def calculate_booking_amount(booking):
    duration = booking.end_time - booking.start_time
    hours = Decimal(duration.total_seconds()) / Decimal("3600")
    return (hours * booking.lsa.hourly_rate).quantize(Decimal("0.01"))
