from django.contrib import admin

from .models import Agency, Package, Shipment, ShipmentSequence, ShipmentStatus, TrackingEvent, WarehouseLocation


class PackageInline(admin.TabularInline):
    model = Package
    extra = 0


class TrackingEventInline(admin.TabularInline):
    model = TrackingEvent
    extra = 0
    readonly_fields = ("previous_status", "status", "agency", "location", "transport_reference", "notes", "created_by", "is_system", "visible_to_customer", "created_at")

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ("order_number", "sender", "recipient", "origin", "destination", "current_status", "created_at")
    list_filter = ("current_status", "transport_mode", "payment_status", "origin", "destination")
    search_fields = ("order_number", "tracking_code", "sender__document_number", "recipient__document_number")
    readonly_fields = ("order_number", "tracking_code", "current_status", "current_agency", "current_location", "created_at", "updated_at", "status_changed_at")
    inlines = (PackageInline, TrackingEventInline)


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "district", "province", "supports_ground", "supports_air", "is_active")
    list_filter = ("department", "supports_ground", "supports_air", "is_active")
    search_fields = ("code", "name", "district", "province")


@admin.register(ShipmentStatus)
class ShipmentStatusAdmin(admin.ModelAdmin):
    list_display = ("sort_order", "code", "name", "is_terminal")
    ordering = ("sort_order",)


admin.site.register(ShipmentSequence)


@admin.register(WarehouseLocation)
class WarehouseLocationAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "agency", "zone", "rack", "level", "is_active")
    list_filter = ("agency", "zone", "is_active")
    search_fields = ("code", "name", "agency__name")


@admin.register(TrackingEvent)
class TrackingEventAdmin(admin.ModelAdmin):
    list_display = ("shipment", "status", "agency", "location", "created_by", "created_at")
    list_filter = ("status", "agency", "visible_to_customer")
    search_fields = ("shipment__order_number", "shipment__tracking_code", "transport_reference")
    readonly_fields = ("shipment", "previous_status", "status", "agency", "location", "transport_reference", "notes", "created_by", "is_system", "visible_to_customer", "created_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
