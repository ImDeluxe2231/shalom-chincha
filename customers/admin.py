from django.contrib import admin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("display_name", "document_type", "document_number", "phone", "district", "is_active")
    list_filter = ("customer_type", "document_type", "is_active", "department", "province")
    search_fields = ("first_name", "last_name", "business_name", "document_number", "phone")
    readonly_fields = ("created_at", "updated_at")
