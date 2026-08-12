from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from bookings.models import BookingRequest, LSAProfile, Parent, Payment, Skill


class Command(BaseCommand):
    help = "Create sample parents, LSAs, skills, bookings, and payments for demos."

    def handle(self, *args, **options):
        speech_skill, _ = Skill.objects.get_or_create(name="Speech Support")
        autism_skill, _ = Skill.objects.get_or_create(name="Autism Support")
        reading_skill, _ = Skill.objects.get_or_create(name="Reading Intervention")

        parent, _ = Parent.objects.get_or_create(
            email="parent.demo@example.com",
            defaults={
                "full_name": "Aisha Khan",
                "phone_number": "+971501234567",
                "child_name": "Zayan Khan",
                "child_age": 8,
                "notes": "Prefers afternoon sessions.",
            },
        )

        lsa_one, _ = LSAProfile.objects.get_or_create(
            email="sara.lsa@example.com",
            defaults={
                "full_name": "Sara Ahmed",
                "phone_number": "+971509876543",
                "bio": "Learning Support Assistant with experience in inclusive classrooms.",
                "hourly_rate": Decimal("120.00"),
                "years_of_experience": 4,
                "availability_status": LSAProfile.AvailabilityStatus.AVAILABLE,
            },
        )
        lsa_one.skills.set([speech_skill, autism_skill])

        lsa_two, _ = LSAProfile.objects.get_or_create(
            email="maria.lsa@example.com",
            defaults={
                "full_name": "Maria Fernandes",
                "phone_number": "+971508765432",
                "bio": "Specialized in reading support and structured learning routines.",
                "hourly_rate": Decimal("100.00"),
                "years_of_experience": 3,
                "availability_status": LSAProfile.AvailabilityStatus.AVAILABLE,
            },
        )
        lsa_two.skills.set([reading_skill, autism_skill])

        start_time = timezone.now() + timedelta(days=1, hours=2)
        end_time = start_time + timedelta(hours=2)

        payment = Payment.objects.filter(
            provider_reference="demo_payment_reference_001"
        ).select_related("booking").first()

        if payment:
            booking = payment.booking
        else:
            booking = BookingRequest.objects.create(
                parent=parent,
                lsa=lsa_one,
                start_time=start_time,
                end_time=end_time,
                special_requirements="Focus on communication and classroom transitions.",
            )
            payment = Payment.objects.create(
                booking=booking,
                provider_reference="demo_payment_reference_001",
                amount=Decimal("240.00"),
                currency="AED",
                status=Payment.PaymentStatus.INITIATED,
                raw_payload={"source": "seed_demo_data"},
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Demo data created: 1 parent, 2 LSAs, 3 skills, 1 booking, 1 payment."
            )
        )
