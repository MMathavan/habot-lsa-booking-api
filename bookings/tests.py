from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from .models import BookingRequest, LSAProfile, Parent, Payment, Skill


class BookingAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.parent = Parent.objects.create(
            full_name="Aisha Khan",
            email="aisha.parent@example.com",
            phone_number="+971501234567",
            child_name="Zayan Khan",
            child_age=8,
        )
        self.autism_skill = Skill.objects.create(name="Autism Support")
        self.reading_skill = Skill.objects.create(name="Reading Intervention")

        self.lsa = LSAProfile.objects.create(
            full_name="Sara Ahmed",
            email="sara.lsa@example.com",
            hourly_rate=Decimal("120.00"),
            years_of_experience=4,
            availability_status=LSAProfile.AvailabilityStatus.AVAILABLE,
        )
        self.lsa.skills.add(self.autism_skill)

        self.other_lsa = LSAProfile.objects.create(
            full_name="Maria Fernandes",
            email="maria.lsa@example.com",
            hourly_rate=Decimal("100.00"),
            years_of_experience=3,
            availability_status=LSAProfile.AvailabilityStatus.AVAILABLE,
        )
        self.other_lsa.skills.add(self.reading_skill)

        self.start_time = timezone.now() + timedelta(days=3)
        self.end_time = self.start_time + timedelta(hours=2)

    def test_booking_creation_success(self):
        response = self.client.post(
            "/api/v1/bookings/",
            {
                "parent_id": self.parent.id,
                "lsa_id": self.lsa.id,
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "special_requirements": "Support with communication routines.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BookingRequest.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertIn("payment", response.data)

    def test_invalid_booking_time_blocked(self):
        response = self.client.post(
            "/api/v1/bookings/",
            {
                "parent_id": self.parent.id,
                "lsa_id": self.lsa.id,
                "start_time": self.end_time.isoformat(),
                "end_time": self.start_time.isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(BookingRequest.objects.count(), 0)

    def test_overlapping_booking_blocked(self):
        BookingRequest.objects.create(
            parent=self.parent,
            lsa=self.lsa,
            start_time=self.start_time,
            end_time=self.end_time,
        )

        response = self.client.post(
            "/api/v1/bookings/",
            {
                "parent_id": self.parent.id,
                "lsa_id": self.lsa.id,
                "start_time": (self.start_time + timedelta(minutes=30)).isoformat(),
                "end_time": (self.end_time + timedelta(minutes=30)).isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(BookingRequest.objects.count(), 1)

    def test_lsa_search_by_skill(self):
        response = self.client.get(
            "/api/v1/lsas/search/",
            {"skills": "Autism Support"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["email"], self.lsa.email)

    def test_payment_webhook_success_confirms_booking(self):
        booking = BookingRequest.objects.create(
            parent=self.parent,
            lsa=self.lsa,
            start_time=self.start_time,
            end_time=self.end_time,
        )
        payment = Payment.objects.create(
            booking=booking,
            provider_reference="test_payment_success",
            amount=Decimal("240.00"),
        )

        response = self.client.post(
            "/api/v1/payments/webhook/",
            {
                "provider_reference": payment.provider_reference,
                "status": Payment.PaymentStatus.SUCCESS,
                "raw_payload": {"event": "payment.succeeded"},
            },
            format="json",
        )

        booking.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(payment.status, Payment.PaymentStatus.SUCCESS)
        self.assertEqual(booking.status, BookingRequest.BookingStatus.CONFIRMED)

    def test_payment_webhook_failure_marks_booking_payment_failed(self):
        booking = BookingRequest.objects.create(
            parent=self.parent,
            lsa=self.lsa,
            start_time=self.start_time,
            end_time=self.end_time,
        )
        payment = Payment.objects.create(
            booking=booking,
            provider_reference="test_payment_failed",
            amount=Decimal("240.00"),
        )

        response = self.client.post(
            "/api/v1/payments/webhook/",
            {
                "provider_reference": payment.provider_reference,
                "status": Payment.PaymentStatus.FAILED,
                "raw_payload": {"event": "payment.failed"},
            },
            format="json",
        )

        booking.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(payment.status, Payment.PaymentStatus.FAILED)
        self.assertEqual(booking.status, BookingRequest.BookingStatus.PAYMENT_FAILED)
