from django.contrib import admin

from .models import BookingRequest, LSAProfile, Parent, Payment, Skill


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ["full_name", "email", "child_name", "child_age", "created_at"]
    search_fields = ["full_name", "email", "child_name"]
    list_filter = ["created_at"]


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(LSAProfile)
class LSAProfileAdmin(admin.ModelAdmin):
    list_display = [
        "full_name",
        "email",
        "hourly_rate",
        "years_of_experience",
        "availability_status",
    ]
    search_fields = ["full_name", "email", "skills__name"]
    list_filter = ["availability_status", "skills"]
    filter_horizontal = ["skills"]


@admin.register(BookingRequest)
class BookingRequestAdmin(admin.ModelAdmin):
    list_display = ["id", "parent", "lsa", "start_time", "end_time", "status"]
    search_fields = ["parent__full_name", "parent__email", "lsa__full_name", "lsa__email"]
    list_filter = ["status", "start_time", "created_at"]
    date_hierarchy = "start_time"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "provider_reference",
        "booking",
        "amount",
        "currency",
        "status",
        "created_at",
    ]
    search_fields = ["provider_reference", "booking__parent__email", "booking__lsa__email"]
    list_filter = ["status", "currency", "created_at"]
