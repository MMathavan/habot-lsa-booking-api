from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Parent(models.Model):
    full_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    child_name = models.CharField(max_length=120)
    child_age = models.PositiveSmallIntegerField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["full_name"]),
        ]
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} - {self.child_name}"


class Skill(models.Model):
    name = models.CharField(max_length=80, unique=True)

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name


class LSAProfile(models.Model):
    class AvailabilityStatus(models.TextChoices):
        AVAILABLE = "available", "Available"
        UNAVAILABLE = "unavailable", "Unavailable"

    full_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2)
    years_of_experience = models.PositiveSmallIntegerField(default=0)
    availability_status = models.CharField(
        max_length=20,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.AVAILABLE,
    )
    skills = models.ManyToManyField(Skill, related_name="lsa_profiles")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["availability_status"]),
            models.Index(fields=["hourly_rate"]),
        ]
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


class BookingRequest(models.Model):
    class BookingStatus(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Pending Payment"
        CONFIRMED = "confirmed", "Confirmed"
        PAYMENT_FAILED = "payment_failed", "Payment Failed"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    parent = models.ForeignKey(
        Parent,
        on_delete=models.CASCADE,
        related_name="booking_requests",
    )
    lsa = models.ForeignKey(
        LSAProfile,
        on_delete=models.PROTECT,
        related_name="booking_requests",
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING_PAYMENT,
    )
    special_requirements = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["lsa", "start_time", "end_time"]),
            models.Index(fields=["parent", "start_time"]),
            models.Index(fields=["status"]),
        ]
        ordering = ["-start_time"]

    def __str__(self):
        return f"{self.parent.full_name} with {self.lsa.full_name}"

    def clean(self):
        if self.start_time and self.start_time < timezone.now():
            raise ValidationError({"start_time": "Booking start time cannot be in the past."})

        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({"end_time": "Booking end time must be after start time."})

        if not self.lsa_id or not self.start_time or not self.end_time:
            return

        overlapping_bookings = BookingRequest.objects.filter(
            lsa_id=self.lsa_id,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
        ).exclude(
            status__in=[
                self.BookingStatus.CANCELLED,
                self.BookingStatus.PAYMENT_FAILED,
            ]
        )

        if self.pk:
            overlapping_bookings = overlapping_bookings.exclude(pk=self.pk)

        if overlapping_bookings.exists():
            raise ValidationError(
                "This LSA already has a booking that overlaps with the requested time."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Payment(models.Model):
    class PaymentStatus(models.TextChoices):
        INITIATED = "initiated", "Initiated"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    booking = models.OneToOneField(
        BookingRequest,
        on_delete=models.CASCADE,
        related_name="payment",
    )
    provider = models.CharField(max_length=80, default="mock_gateway")
    provider_reference = models.CharField(max_length=120, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="AED")
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.INITIATED,
    )
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["provider_reference"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.provider_reference} - {self.status}"
