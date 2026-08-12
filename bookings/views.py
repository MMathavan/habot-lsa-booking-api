from django.db import transaction
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BookingRequest, LSAProfile, Payment
from .serializers import (
    BookingRequestSerializer,
    LSAProfileSerializer,
    PaymentWebhookSerializer,
)
from .services import (
    MockPaymentGatewayClient,
    PaymentGatewayError,
    calculate_booking_amount,
)


class BookingCreateAPIView(APIView):
    def post(self, request):
        serializer = BookingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                booking = serializer.save()
                amount = calculate_booking_amount(booking)
                gateway_result = MockPaymentGatewayClient().create_payment(
                    booking=booking,
                    amount=amount,
                )
                payment = Payment.objects.create(
                    booking=booking,
                    provider_reference=gateway_result.provider_reference,
                    amount=amount,
                    status=Payment.PaymentStatus.INITIATED,
                    raw_payload=gateway_result.raw_response,
                )
        except PaymentGatewayError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        response_serializer = BookingRequestSerializer(booking)
        response_data = response_serializer.data
        response_data["payment"] = {
            "provider_reference": payment.provider_reference,
            "amount": str(payment.amount),
            "currency": payment.currency,
            "status": payment.status,
        }
        return Response(response_data, status=status.HTTP_201_CREATED)


class LSASearchAPIView(APIView):
    def get(self, request):
        queryset = LSAProfile.objects.filter(
            availability_status=LSAProfile.AvailabilityStatus.AVAILABLE
        ).prefetch_related("skills")

        skills = request.query_params.get("skills")
        if skills:
            skill_names = [
                skill.strip()
                for skill in skills.split(",")
                if skill.strip()
            ]
            queryset = queryset.filter(skills__name__in=skill_names).distinct()

        start_time = parse_datetime(request.query_params.get("start_time", ""))
        end_time = parse_datetime(request.query_params.get("end_time", ""))

        if start_time and end_time:
            queryset = queryset.exclude(
                booking_requests__start_time__lt=end_time,
                booking_requests__end_time__gt=start_time,
            ).distinct()

        serializer = LSAProfileSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PaymentWebhookAPIView(APIView):
    def post(self, request):
        serializer = PaymentWebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider_reference = serializer.validated_data["provider_reference"]
        payment_status = serializer.validated_data["status"]
        raw_payload = serializer.validated_data.get("raw_payload", request.data)

        with transaction.atomic():
            payment = Payment.objects.select_related("booking").get(
                provider_reference=provider_reference
            )
            payment.status = payment_status
            payment.raw_payload = raw_payload
            payment.save(update_fields=["status", "raw_payload", "updated_at"])

            if payment_status == Payment.PaymentStatus.SUCCESS:
                payment.booking.status = BookingRequest.BookingStatus.CONFIRMED
            elif payment_status == Payment.PaymentStatus.FAILED:
                payment.booking.status = BookingRequest.BookingStatus.PAYMENT_FAILED

            payment.booking.save(update_fields=["status", "updated_at"])

        return Response(
            {
                "message": "Payment webhook processed successfully.",
                "booking_id": payment.booking_id,
                "booking_status": payment.booking.status,
                "payment_status": payment.status,
            },
            status=status.HTTP_200_OK,
        )
