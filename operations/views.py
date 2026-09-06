import base64
import mimetypes
from io import BytesIO
from pathlib import Path

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.decorators import admin_role_required
from shipments.models import Shipment

from .forms import DeliveryForm, IncidentForm, IncidentResolutionForm, IncidentReviewForm
from .models import Delivery, Incident
from .services import complete_delivery, report_incident, resolve_incident, review_incident


def _shipment_queryset():
    return Shipment.objects.select_related(
        "sender", "recipient", "origin", "destination", "current_status",
        "current_agency", "current_location", "updated_by",
    ).prefetch_related("packages", "incidents")


def _qr_base64(payload):
    qr = qrcode.QRCode(version=2, box_size=7, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    image = qr.make_image(fill_color="#102746", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


@login_required
def delivery_dashboard(request):
    query = request.GET.get("q", "").strip()
    ready = _shipment_queryset().filter(current_status__code="READY_PICKUP")
    if query:
        ready = ready.filter(
            Q(order_number__icontains=query)
            | Q(tracking_code__icontains=query)
            | Q(recipient__document_number__icontains=query)
            | Q(recipient__first_name__icontains=query)
            | Q(recipient__last_name__icontains=query)
            | Q(recipient__business_name__icontains=query)
        )
    page_obj = Paginator(ready, 10).get_page(request.GET.get("page"))
    recent_deliveries = Delivery.objects.select_related(
        "shipment", "agency", "delivered_by"
    ).order_by("-delivered_at")[:8]
    context = {
        "shipments": page_obj.object_list,
        "page_obj": page_obj,
        "query": query,
        "ready_count": Shipment.objects.filter(current_status__code="READY_PICKUP").count(),
        "today_count": Delivery.objects.filter(delivered_at__date=timezone.localdate()).count(),
        "total_deliveries": Delivery.objects.count(),
        "observed_count": Delivery.objects.filter(package_condition=Delivery.PackageCondition.OBSERVED).count(),
        "recent_deliveries": recent_deliveries,
        "section": "deliveries",
    }
    return render(request, "operations/delivery_dashboard.html", context)


@login_required
def delivery_history(request):
    query = request.GET.get("q", "").strip()
    method = request.GET.get("method", "").strip()
    date_from = request.GET.get("from", "").strip()
    date_to = request.GET.get("to", "").strip()
    deliveries = Delivery.objects.select_related("shipment__recipient", "agency", "delivered_by")
    if query:
        deliveries = deliveries.filter(
            Q(shipment__order_number__icontains=query)
            | Q(receiver_name__icontains=query)
            | Q(receiver_document_number__icontains=query)
            | Q(shipment__recipient__document_number__icontains=query)
        )
    if method in Delivery.DeliveryMethod.values:
        deliveries = deliveries.filter(delivery_method=method)
    if date_from:
        deliveries = deliveries.filter(delivered_at__date__gte=date_from)
    if date_to:
        deliveries = deliveries.filter(delivered_at__date__lte=date_to)
    page_obj = Paginator(deliveries, 15).get_page(request.GET.get("page"))
    return render(request, "operations/delivery_history.html", {
        "deliveries": page_obj.object_list,
        "page_obj": page_obj,
        "query": query,
        "selected_method": method,
        "date_from": date_from,
        "date_to": date_to,
        "methods": Delivery.DeliveryMethod.choices,
        "section": "deliveries",
    })


@login_required
def delivery_create(request, shipment_id):
    shipment = get_object_or_404(_shipment_queryset(), pk=shipment_id)
    if shipment.current_status.code != "READY_PICKUP":
        messages.error(request, "Este envío todavía no está disponible para entrega.")
        return redirect("delivery_dashboard")
    if hasattr(shipment, "delivery"):
        return redirect("delivery_detail", pk=shipment.delivery.pk)
    form = DeliveryForm(request.POST or None, shipment=shipment)
    if request.method == "POST" and form.is_valid():
        delivery = form.save(commit=False)
        try:
            complete_delivery(shipment_id=shipment.pk, delivery=delivery, user=request.user)
        except ValidationError as exc:
            form.add_error(None, "; ".join(exc.messages))
        else:
            messages.success(request, f"Entrega de {shipment.order_number} registrada correctamente.")
            return redirect("delivery_detail", pk=delivery.pk)
    return render(request, "operations/delivery_form.html", {
        "shipment": shipment, "form": form, "section": "deliveries",
    })


@login_required
def delivery_detail(request, pk):
    delivery = get_object_or_404(
        Delivery.objects.select_related(
            "shipment__sender", "shipment__recipient", "shipment__origin", "shipment__destination",
            "agency", "delivered_by",
        ).prefetch_related("shipment__packages"),
        pk=pk,
    )
    return render(request, "operations/delivery_detail.html", {"delivery": delivery, "section": "deliveries"})


@login_required
def delivery_receipt(request, pk):
    delivery = get_object_or_404(
        Delivery.objects.select_related(
            "shipment__sender", "shipment__recipient", "shipment__origin", "shipment__destination",
            "agency", "delivered_by",
        ).prefetch_related("shipment__packages"), pk=pk,
    )
    verify_url = request.build_absolute_uri(reverse("delivery_verify", args=[delivery.verification_code]))
    return render(request, "operations/delivery_receipt.html", {
        "delivery": delivery,
        "qr_data": _qr_base64(verify_url),
        "section": "deliveries",
    })


def delivery_verify(request, verification_code):
    delivery = get_object_or_404(
        Delivery.objects.select_related("shipment", "agency", "delivered_by"),
        verification_code=verification_code,
    )
    return render(request, "operations/delivery_verify.html", {"delivery": delivery})


@login_required
def incident_list(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    severity = request.GET.get("severity", "").strip()
    incidents = Incident.objects.select_related(
        "shipment", "agency", "reported_by", "assigned_to", "previous_status"
    )
    if query:
        incidents = incidents.filter(
            Q(code__icontains=query)
            | Q(shipment__order_number__icontains=query)
            | Q(shipment__tracking_code__icontains=query)
            | Q(description__icontains=query)
        )
    if status in Incident.Status.values:
        incidents = incidents.filter(status=status)
    if severity in Incident.Severity.values:
        incidents = incidents.filter(severity=severity)
    page_obj = Paginator(incidents, 12).get_page(request.GET.get("page"))
    return render(request, "operations/incident_list.html", {
        "incidents": page_obj.object_list,
        "page_obj": page_obj,
        "query": query,
        "selected_status": status,
        "selected_severity": severity,
        "statuses": Incident.Status.choices,
        "severities": Incident.Severity.choices,
        "open_count": Incident.objects.filter(status=Incident.Status.OPEN).count(),
        "review_count": Incident.objects.filter(status=Incident.Status.IN_REVIEW).count(),
        "critical_count": Incident.objects.exclude(status=Incident.Status.RESOLVED).filter(severity=Incident.Severity.CRITICAL).count(),
        "resolved_count": Incident.objects.filter(status=Incident.Status.RESOLVED).count(),
        "section": "incidents",
    })


@login_required
def incident_create(request, shipment_id):
    shipment = get_object_or_404(_shipment_queryset(), pk=shipment_id)
    form = IncidentForm(request.POST or None, request.FILES or None, shipment=shipment)
    if request.method == "POST" and form.is_valid():
        incident = form.save(commit=False)
        try:
            report_incident(shipment_id=shipment.pk, incident=incident, user=request.user)
        except ValidationError as exc:
            form.add_error(None, "; ".join(exc.messages))
        else:
            messages.success(request, f"Incidencia {incident.code} registrada.")
            return redirect("incident_detail", pk=incident.pk)
    return render(request, "operations/incident_form.html", {
        "shipment": shipment, "form": form, "section": "incidents",
    })


@login_required
def incident_detail(request, pk):
    incident = get_object_or_404(
        Incident.objects.select_related(
            "shipment__sender", "shipment__recipient", "shipment__current_status", "previous_status",
            "agency", "reported_by", "assigned_to", "resolved_by",
        ).prefetch_related("actions__performed_by"), pk=pk,
    )
    review_form = IncidentReviewForm(initial={"assigned_to": incident.assigned_to, "public_message": incident.public_message})
    resolution_form = IncidentResolutionForm(initial={"public_message": incident.public_message})
    return render(request, "operations/incident_detail.html", {
        "incident": incident,
        "review_form": review_form,
        "resolution_form": resolution_form,
        "section": "incidents",
    })


@login_required
def incident_evidence(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    if not incident.evidence:
        raise Http404("La incidencia no tiene evidencia adjunta.")
    filename = Path(incident.evidence.name).name
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    response = FileResponse(incident.evidence.open("rb"), content_type=content_type, filename=filename)
    response["X-Content-Type-Options"] = "nosniff"
    return response


@admin_role_required
def incident_review(request, pk):
    if request.method != "POST":
        return redirect("incident_detail", pk=pk)
    incident = get_object_or_404(Incident, pk=pk)
    form = IncidentReviewForm(request.POST)
    if form.is_valid():
        try:
            review_incident(
                incident_id=incident.pk,
                assigned_to=form.cleaned_data["assigned_to"],
                public_message=form.cleaned_data["public_message"],
                user=request.user,
            )
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        else:
            messages.success(request, f"Incidencia {incident.code} asignada y puesta en revisión.")
    else:
        messages.error(request, "Selecciona un responsable válido.")
    return redirect("incident_detail", pk=pk)


@admin_role_required
def incident_resolve(request, pk):
    if request.method != "POST":
        return redirect("incident_detail", pk=pk)
    incident = get_object_or_404(Incident, pk=pk)
    form = IncidentResolutionForm(request.POST)
    if form.is_valid():
        try:
            resolve_incident(
                incident_id=incident.pk,
                resolution=form.cleaned_data["resolution"],
                public_message=form.cleaned_data["public_message"],
                user=request.user,
            )
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        else:
            messages.success(request, f"Incidencia {incident.code} resuelta. El envío retomó su estado anterior.")
    else:
        messages.error(request, "Completa la solución y confirma la reanudación del envío.")
    return redirect("incident_detail", pk=pk)
