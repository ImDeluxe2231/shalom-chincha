from django.contrib import admin

from .models import ReportExport


@admin.register(ReportExport)
class ReportExportAdmin(admin.ModelAdmin):
    list_display = ("report_type", "file_format", "row_count", "requested_by", "created_at")
    list_filter = ("report_type", "file_format", "created_at")
    search_fields = ("requested_by__username", "requested_by__first_name", "requested_by__last_name")
    readonly_fields = ("report_type", "file_format", "filters", "row_count", "requested_by", "created_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
