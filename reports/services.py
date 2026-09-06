from collections import OrderedDict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import Coalesce, TruncDate

from operations.models import Delivery, Incident
from shipments.models import Shipment

from .forms import bound_report_filter


ACTIVE_STATUS_CODES = {
    "REGISTERED", "RECEIVED", "IN_WAREHOUSE", "DISPATCHED",
    "IN_TRANSIT", "AT_DESTINATION", "READY_PICKUP", "INCIDENT",
}


def _shipment_scope(cleaned):
    queryset = Shipment.objects.select_related(
        "sender", "recipient", "origin", "destination", "current_status", "created_by"
    ).filter(created_at__date__range=(cleaned["date_from"], cleaned["date_to"]))
    agency = cleaned.get("agency")
    if agency:
        queryset = queryset.filter(Q(origin=agency) | Q(destination=agency))
    if cleaned.get("transport_mode"):
        queryset = queryset.filter(transport_mode=cleaned["transport_mode"])
    return queryset.distinct()


def _delivery_scope(cleaned):
    queryset = Delivery.objects.select_related(
        "shipment__sender", "shipment__recipient", "shipment__origin", "shipment__destination",
        "agency", "delivered_by",
    ).filter(delivered_at__date__range=(cleaned["date_from"], cleaned["date_to"]))
    if cleaned.get("agency"):
        queryset = queryset.filter(agency=cleaned["agency"])
    if cleaned.get("transport_mode"):
        queryset = queryset.filter(shipment__transport_mode=cleaned["transport_mode"])
    return queryset


def _incident_scope(cleaned):
    queryset = Incident.objects.select_related(
        "shipment", "agency", "assigned_to", "reported_by", "resolved_by"
    ).filter(reported_at__date__range=(cleaned["date_from"], cleaned["date_to"]))
    if cleaned.get("agency"):
        queryset = queryset.filter(agency=cleaned["agency"])
    if cleaned.get("transport_mode"):
        queryset = queryset.filter(shipment__transport_mode=cleaned["transport_mode"])
    return queryset


def resolve_filters(data=None):
    form = bound_report_filter(data)
    if not form.is_valid():
        return form, None
    return form, form.cleaned_data


def serialize_filters(cleaned):
    return {
        "date_from": cleaned["date_from"].isoformat(),
        "date_to": cleaned["date_to"].isoformat(),
        "agency": cleaned["agency"].code if cleaned.get("agency") else "ALL",
        "transport_mode": cleaned.get("transport_mode") or "ALL",
    }


def build_dashboard_context(data, user):
    form, cleaned = resolve_filters(data)
    if cleaned is None:
        fallback = bound_report_filter()
        fallback.is_valid()
        cleaned = fallback.cleaned_data

    shipments = _shipment_scope(cleaned)
    deliveries = _delivery_scope(cleaned)
    incidents = _incident_scope(cleaned)
    shipment_count = shipments.count()
    delivered_count = deliveries.count()
    closed_base = shipments.exclude(current_status__code="CANCELED").count()
    incident_count = incidents.count()
    period_delivered_shipments = shipments.filter(current_status__code="DELIVERED").count()
    impacted_shipments = shipments.filter(
        incidents__reported_at__date__range=(cleaned["date_from"], cleaned["date_to"])
    ).distinct().count()
    active_incidents = Incident.objects.exclude(status=Incident.Status.RESOLVED)
    if cleaned.get("agency"):
        active_incidents = active_incidents.filter(agency=cleaned["agency"])
    if cleaned.get("transport_mode"):
        active_incidents = active_incidents.filter(shipment__transport_mode=cleaned["transport_mode"])
    active_shipments = Shipment.objects.filter(current_status__code__in=ACTIVE_STATUS_CODES)
    if cleaned.get("agency"):
        active_shipments = active_shipments.filter(
            Q(origin=cleaned["agency"]) | Q(destination=cleaned["agency"]) | Q(current_agency=cleaned["agency"])
        )
    if cleaned.get("transport_mode"):
        active_shipments = active_shipments.filter(transport_mode=cleaned["transport_mode"])

    money_expression = ExpressionWrapper(
        F("shipping_cost") + F("insurance_cost") - F("discount"),
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )
    paid_revenue = shipments.filter(payment_status=Shipment.PaymentStatus.PAID).aggregate(
        total=Coalesce(Sum(money_expression), Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2))
    )["total"]

    durations = [
        (item.delivered_at - item.shipment.created_at).total_seconds() / 3600
        for item in deliveries
    ]
    average_hours = round(sum(durations) / len(durations), 1) if durations else 0
    on_time = sum(
        1 for item in deliveries
        if item.shipment.estimated_delivery_date and item.delivered_at.date() <= item.shipment.estimated_delivery_date
    )
    estimated_deliveries = sum(1 for item in deliveries if item.shipment.estimated_delivery_date)

    day_counts = {
        row["day"]: row["total"]
        for row in shipments.annotate(day=TruncDate("created_at")).values("day").annotate(total=Count("id")).order_by("day")
    }
    current = cleaned["date_from"]
    daily_labels, daily_values = [], []
    while current <= cleaned["date_to"]:
        daily_labels.append(current.strftime("%d/%m"))
        daily_values.append(day_counts.get(current, 0))
        current += timedelta(days=1)

    status_rows = list(
        shipments.values("current_status__name", "current_status__color")
        .annotate(total=Count("id")).order_by("current_status__sort_order")
    )
    agency_rows = list(
        deliveries.values("agency__code").annotate(total=Count("id")).order_by("-total", "agency__code")[:8]
    )
    severity_order = OrderedDict((code, 0) for code, _ in Incident.Severity.choices)
    for row in incidents.values("severity").annotate(total=Count("id")):
        severity_order[row["severity"]] = row["total"]

    return {
        "filter_form": form,
        "period_from": cleaned["date_from"],
        "period_to": cleaned["date_to"],
        "shipment_count": shipment_count,
        "delivered_count": delivered_count,
        "active_shipments": active_shipments.distinct().count(),
        "active_incident_count": active_incidents.count(),
        "pending_payment_count": shipments.filter(payment_status=Shipment.PaymentStatus.PENDING).count(),
        "paid_revenue": paid_revenue,
        "delivery_rate": round((period_delivered_shipments / closed_base) * 100, 1) if closed_base else 0,
        "incident_rate": round((impacted_shipments / shipment_count) * 100, 1) if shipment_count else 0,
        "average_delivery_hours": average_hours,
        "on_time_rate": round((on_time / estimated_deliveries) * 100, 1) if estimated_deliveries else 0,
        "show_financial": user.is_admin_role or user.role == "ADMINISTRATIVE",
        "can_export_reports": user.is_admin_role,
        "daily_chart": {"labels": daily_labels, "values": daily_values},
        "status_chart": {
            "labels": [row["current_status__name"] for row in status_rows],
            "values": [row["total"] for row in status_rows],
            "colors": [row["current_status__color"] for row in status_rows],
        },
        "agency_chart": {
            "labels": [row["agency__code"] for row in agency_rows],
            "values": [row["total"] for row in agency_rows],
        },
        "severity_chart": {
            "labels": [label for _, label in Incident.Severity.choices],
            "values": list(severity_order.values()),
        },
        "recent_incidents": active_incidents.select_related("shipment", "agency").order_by("-severity", "-reported_at")[:5],
        "recent_deliveries": deliveries.order_by("-delivered_at")[:5],
    }


REPORT_COLUMNS = {
    "SHIPMENTS": ["Orden", "Registro", "Remitente", "Destinatario", "Ruta", "Transporte", "Estado", "Pago", "Total (S/)", "Responsable"],
    "DELIVERIES": ["Orden", "Fecha de entrega", "Receptor", "Modalidad", "Agencia", "Bultos", "Condición", "Responsable"],
    "INCIDENTS": ["Código", "Fecha de reporte", "Orden", "Tipo", "Gravedad", "Situación", "Agencia", "Asignado a", "Fecha de resolución"],
}


def report_queryset(report_type, cleaned):
    if report_type == "DELIVERIES":
        return _delivery_scope(cleaned).order_by("-delivered_at")
    if report_type == "INCIDENTS":
        return _incident_scope(cleaned).order_by("-reported_at")
    return _shipment_scope(cleaned).order_by("-created_at")


def report_rows(report_type, queryset):
    if report_type == "DELIVERIES":
        return [[
            item.shipment.order_number,
            item.delivered_at.strftime("%d/%m/%Y %H:%M"),
            item.receiver_name,
            item.get_delivery_method_display(),
            item.agency.code,
            item.packages_delivered,
            item.get_package_condition_display(),
            item.delivered_by.display_name,
        ] for item in queryset]
    if report_type == "INCIDENTS":
        return [[
            item.code,
            item.reported_at.strftime("%d/%m/%Y %H:%M"),
            item.shipment.order_number,
            item.get_incident_type_display(),
            item.get_severity_display(),
            item.get_status_display(),
            item.agency.code,
            item.assigned_to.display_name if item.assigned_to else "Sin asignar",
            item.resolved_at.strftime("%d/%m/%Y %H:%M") if item.resolved_at else "—",
        ] for item in queryset]
    return [[
        item.order_number,
        item.created_at.strftime("%d/%m/%Y %H:%M"),
        item.sender.display_name,
        item.recipient.display_name,
        f"{item.origin.code} → {item.destination.code}",
        item.get_transport_mode_display(),
        item.current_status_label,
        item.get_payment_status_display(),
        f"{item.total_cost:.2f}",
        item.created_by.display_name,
    ] for item in queryset]
