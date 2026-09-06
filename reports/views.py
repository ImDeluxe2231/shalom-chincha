from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import redirect, render

from accounts.decorators import admin_role_required
from operations.models import Delivery, Incident
from shipments.models import Shipment

from .exporters import csv_bytes, pdf_bytes, xlsx_bytes
from .models import ReportExport
from .services import REPORT_COLUMNS, report_queryset, report_rows, resolve_filters, serialize_filters


VALID_REPORTS = set(REPORT_COLUMNS)
VALID_FORMATS = {"CSV", "XLSX", "PDF"}


@admin_role_required
def report_center(request):
    report_type = request.GET.get("report", "SHIPMENTS").upper()
    if report_type not in VALID_REPORTS:
        report_type = "SHIPMENTS"
    form, cleaned = resolve_filters(request.GET)
    if cleaned:
        queryset = report_queryset(report_type, cleaned)
    else:
        empty_models = {"SHIPMENTS": Shipment, "DELIVERIES": Delivery, "INCIDENTS": Incident}
        queryset = empty_models[report_type].objects.none()
    page_obj = Paginator(queryset, 15).get_page(request.GET.get("page"))
    return render(request, "reports/report_center.html", {
        "filter_form": form,
        "report_type": report_type,
        "report_label": dict(ReportExport.ReportType.choices)[report_type],
        "items": page_obj.object_list,
        "page_obj": page_obj,
        "total_rows": queryset.count(),
        "recent_exports": ReportExport.objects.select_related("requested_by")[:8],
        "section": "reports",
    })


@admin_role_required
def report_export(request, report_type, file_format):
    report_type = report_type.upper()
    file_format = file_format.upper()
    if report_type not in VALID_REPORTS or file_format not in VALID_FORMATS:
        messages.error(request, "El reporte o formato solicitado no es válido.")
        return redirect("report_center")
    form, cleaned = resolve_filters(request.GET)
    if not cleaned:
        messages.error(request, "Corrige el periodo antes de exportar el reporte.")
        return redirect(f"/reportes/?report={report_type}")

    queryset = report_queryset(report_type, cleaned)
    rows = report_rows(report_type, queryset)
    headers = REPORT_COLUMNS[report_type]
    report_name = dict(ReportExport.ReportType.choices)[report_type]
    basename = f"shalom_{report_type.lower()}_{cleaned['date_from']}_{cleaned['date_to']}"
    if file_format == "CSV":
        content = csv_bytes(headers, rows)
        content_type = "text/csv; charset=utf-8"
        extension = "csv"
    elif file_format == "XLSX":
        content = xlsx_bytes(headers, rows)
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        extension = "xlsx"
    else:
        content = pdf_bytes(
            f"Shalom Chincha - Reporte de {report_name}",
            f"Periodo: {cleaned['date_from']:%d/%m/%Y} al {cleaned['date_to']:%d/%m/%Y}",
            headers,
            rows,
        )
        content_type = "application/pdf"
        extension = "pdf"

    ReportExport.objects.create(
        report_type=report_type,
        file_format=file_format,
        filters=serialize_filters(cleaned),
        row_count=len(rows),
        requested_by=request.user,
    )
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{basename}.{extension}"'
    response["X-Content-Type-Options"] = "nosniff"
    return response
