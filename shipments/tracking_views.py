import time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import admin_role_required, operational_role_required
from operations.models import Incident

from .forms import OperationalTransitionForm, PublicTrackingForm, WarehouseLocationForm
from .models import Agency, Shipment, ShipmentStatus, TrackingEvent, WarehouseLocation
from .tracking_services import register_transition, transition_context


def _shipment_queryset():
    return Shipment.objects.select_related(
        "sender", "recipient", "origin", "destination", "current_status",
        "current_agency", "current_location", "updated_by",
    ).prefetch_related(
        "packages", "tracking_events__status", "tracking_events__previous_status",
        "tracking_events__agency", "tracking_events__location", "tracking_events__created_by",
    )


def _can_operate(user):
    return user.is_admin_role or user.role == "OPERATIONAL"


@login_required
def tracking_dashboard(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    agency = request.GET.get("agency", "").strip()
    shipments = _shipment_queryset()
    if query:
        shipments = shipments.filter(
            Q(order_number__icontains=query)
            | Q(tracking_code__icontains=query)
            | Q(sender__document_number__icontains=query)
            | Q(recipient__document_number__icontains=query)
            | Q(sender__first_name__icontains=query)
            | Q(sender__last_name__icontains=query)
            | Q(recipient__first_name__icontains=query)
            | Q(recipient__last_name__icontains=query)
        )
    if status:
        shipments = shipments.filter(current_status__code=status)
    if agency.isdigit():
        shipments = shipments.filter(current_agency_id=agency)

    page_obj = Paginator(shipments, 12).get_page(request.GET.get("page"))
    active_codes = ["REGISTERED", "RECEIVED", "IN_WAREHOUSE", "DISPATCHED", "IN_TRANSIT", "AT_DESTINATION", "READY_PICKUP"]
    context = {
        "shipments": page_obj.object_list,
        "page_obj": page_obj,
        "statuses": ShipmentStatus.objects.filter(code__in=active_codes),
        "agencies": Agency.objects.filter(is_active=True),
        "query": query,
        "selected_status": status,
        "selected_agency": agency,
        "can_operate": _can_operate(request.user),
        "warehouse_count": Shipment.objects.filter(current_status__code__in=["RECEIVED", "IN_WAREHOUSE"]).count(),
        "transit_count": Shipment.objects.filter(current_status__code__in=["DISPATCHED", "IN_TRANSIT"]).count(),
        "destination_count": Shipment.objects.filter(current_status__code__in=["AT_DESTINATION", "READY_PICKUP"]).count(),
        "recent_events": TrackingEvent.objects.select_related("shipment", "status", "agency", "created_by").order_by("-created_at")[:6],
        "section": "tracking",
    }
    return render(request, "shipments/tracking_dashboard.html", context)


@login_required
def tracking_detail(request, pk):
    shipment = get_object_or_404(_shipment_queryset(), pk=pk)
    active_incident = shipment.incidents.exclude(status=Incident.Status.RESOLVED).first()
    action = transition_context(shipment) if _can_operate(request.user) else None
    form = None
    if action:
        form = OperationalTransitionForm(shipment=shipment, target_code=action["code"])
    return render(request, "shipments/tracking_detail.html", {
        "shipment": shipment,
        "action": action,
        "form": form,
        "can_operate": _can_operate(request.user),
        "active_incident": active_incident,
        "section": "tracking",
    })


@operational_role_required
def tracking_transition(request, pk, target_code):
    if request.method != "POST":
        return redirect("tracking_detail", pk=pk)
    shipment = get_object_or_404(_shipment_queryset(), pk=pk)
    action = transition_context(shipment)
    if not action or action["code"] != target_code:
        messages.error(request, "La transición solicitada ya no está disponible para este envío.")
        return redirect("tracking_detail", pk=pk)
    form = OperationalTransitionForm(request.POST, shipment=shipment, target_code=target_code)
    if form.is_valid():
        try:
            register_transition(
                shipment_id=shipment.pk,
                target_code=target_code,
                user=request.user,
                location=form.cleaned_data.get("location"),
                transport_reference=form.cleaned_data.get("transport_reference", ""),
                notes=form.cleaned_data.get("notes", ""),
            )
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        else:
            messages.success(request, f"El envío {shipment.order_number} fue actualizado a {action['status'].name}.")
            return redirect("tracking_detail", pk=pk)
    return render(request, "shipments/tracking_detail.html", {
        "shipment": shipment,
        "action": action,
        "form": form,
        "can_operate": True,
        "section": "tracking",
    })


@admin_role_required
def warehouse_location_list(request):
    locations = WarehouseLocation.objects.select_related("agency")
    return render(request, "shipments/warehouse_location_list.html", {"locations": locations, "section": "locations"})


@admin_role_required
def warehouse_location_create(request):
    form = WarehouseLocationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        location = form.save()
        messages.success(request, f"Ubicación {location.full_label} creada.")
        return redirect("warehouse_location_list")
    return render(request, "shipments/warehouse_location_form.html", {"form": form, "title": "Nueva ubicación", "section": "locations"})


@admin_role_required
def warehouse_location_update(request, pk):
    location = get_object_or_404(WarehouseLocation, pk=pk)
    form = WarehouseLocationForm(request.POST or None, instance=location)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Ubicación {location.full_label} actualizada.")
        return redirect("warehouse_location_list")
    return render(request, "shipments/warehouse_location_form.html", {"form": form, "title": f"Editar {location.code}", "section": "locations"})


def public_tracking(request):
    now = time.time()
    failed_attempts = [stamp for stamp in request.session.get("tracking_attempts", []) if now - stamp < 300]
    locked = len(failed_attempts) >= 5
    initial = {"order_number": request.GET.get("order", ""), "tracking_code": request.GET.get("code", "")}
    submitted = request.method == "POST" or bool(initial["order_number"] and initial["tracking_code"])
    form_data = (request.POST or initial) if submitted else None
    form = PublicTrackingForm(form_data)
    shipment = None
    if submitted and not locked and form.is_valid():
        shipment = _shipment_queryset().filter(
            order_number=form.cleaned_data["order_number"],
            tracking_code=form.cleaned_data["tracking_code"],
        ).first()
        if shipment is None:
            failed_attempts.append(now)
            request.session["tracking_attempts"] = failed_attempts
            form.add_error(None, "No encontramos un envío con los datos ingresados. Verifícalos e inténtalo nuevamente.")
        else:
            request.session.pop("tracking_attempts", None)
    elif locked and submitted:
        form.is_valid()
        form.add_error(None, "Se alcanzó el límite de consultas. Espera cinco minutos antes de volver a intentarlo.")
    public_events = shipment.tracking_events.filter(visible_to_customer=True) if shipment else []
    active_incident = shipment.incidents.exclude(status=Incident.Status.RESOLVED).first() if shipment else None
    return render(request, "shipments/public_tracking.html", {
        "form": form,
        "shipment": shipment,
        "public_events": public_events,
        "active_incident": active_incident,
        "locked": locked,
    })
