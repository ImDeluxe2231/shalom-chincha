from django.contrib import admin

from .models import Delivery, Incident, IncidentAction


class IncidentActionInline(admin.TabularInline):
    model = IncidentAction
    extra = 0
    readonly_fields = ("action", "notes", "performed_by", "created_at")

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("shipment", "receiver_name", "delivery_method", "agency", "delivered_by", "delivered_at")
    list_filter = ("delivery_method", "package_condition", "agency", "delivered_at")
    search_fields = ("shipment__order_number", "receiver_name", "receiver_document_number")
    readonly_fields = (
        "shipment", "agency", "delivery_method", "receiver_type", "receiver_name",
        "receiver_document_type", "receiver_document_number", "receiver_phone", "relationship",
        "verification_method", "package_condition", "condition_notes", "packages_delivered",
        "payment_confirmed", "notes", "verification_code", "delivered_by", "delivered_at", "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("code", "shipment", "incident_type", "severity", "status", "agency", "reported_at")
    list_filter = ("status", "severity", "incident_type", "agency")
    search_fields = ("code", "shipment__order_number", "description")
    readonly_fields = (
        "code", "shipment", "previous_status", "agency", "incident_type", "severity",
        "status", "description", "public_message", "evidence", "assigned_to", "resolution",
        "reported_by", "resolved_by", "reported_at", "resolved_at", "updated_at",
    )
    inlines = (IncidentActionInline,)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
