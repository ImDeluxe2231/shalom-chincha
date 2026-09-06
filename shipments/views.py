import base64
from io import BytesIO

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.decorators import admin_role_required, administrative_role_required

from .forms import AgencyForm, CancellationForm, PackageFormSet, ShipmentForm
from .models import Agency, Shipment, ShipmentStatus, TrackingEvent


def _can_write(user):
    return user.is_admin_role or user.role == "ADMINISTRATIVE"


@login_required
def shipment_list(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    mode = request.GET.get("mode", "").strip()
    date_from = request.GET.get("from", "").strip()
    date_to = request.GET.get("to", "").strip()

    shipments = Shipment.objects.select_related(
        "sender", "recipient", "origin", "destination", "current_status", "created_by"
    ).prefetch_related("packages")
    if query:
        shipments = shipments.filter(
            Q(order_number__icontains=query)
            | Q(tracking_code__icontains=query)
            | Q(sender__first_name__icontains=query)
            | Q(sender__last_name__icontains=query)
            | Q(sender__business_name__icontains=query)
            | Q(recipient__first_name__icontains=query)
            | Q(recipient__last_name__icontains=query)
            | Q(recipient__business_name__icontains=query)
            | Q(sender__document_number__icontains=query)
            | Q(recipient__document_number__icontains=query)
        )
    if status:
        shipments = shipments.filter(current_status__code=status)
    if mode in Shipment.TransportMode.values:
        shipments = shipments.filter(transport_mode=mode)
    if date_from:
        shipments = shipments.filter(created_at__date__gte=date_from)
    if date_to:
        shipments = shipments.filter(created_at__date__lte=date_to)

    page_obj = Paginator(shipments, 12).get_page(request.GET.get("page"))
    context = {
        "shipments": page_obj.object_list,
        "page_obj": page_obj,
        "statuses": ShipmentStatus.objects.all(),
        "transport_modes": Shipment.TransportMode.choices,
        "query": query,
        "selected_status": status,
        "selected_mode": mode,
        "date_from": date_from,
        "date_to": date_to,
        "can_write": _can_write(request.user),
        "total_shipments": Shipment.objects.count(),
        "today_shipments": Shipment.objects.filter(created_at__date=timezone.localdate()).count(),
        "pending_payment": Shipment.objects.filter(payment_status=Shipment.PaymentStatus.PENDING).count(),
        "section": "shipments",
    }
    return render(request, "shipments/shipment_list.html", context)


@login_required
def shipment_detail(request, pk):
    from operations.models import Incident

    shipment = get_object_or_404(
        Shipment.objects.select_related(
            "sender", "recipient", "origin", "destination", "current_status", "created_by", "updated_by"
        ).prefetch_related("packages", "tracking_events__status", "tracking_events__agency", "tracking_events__created_by"),
        pk=pk,
    )
    return render(
        request,
        "shipments/shipment_detail.html",
        {
            "shipment": shipment,
            "can_write": _can_write(request.user),
            "can_cancel": (
                request.user.is_admin_role
                and not shipment.current_status.is_terminal
                and not Incident.objects.filter(shipment=shipment).exclude(status=Incident.Status.RESOLVED).exists()
            ),
            "cancellation_form": CancellationForm(),
            "section": "shipments",
        },
    )


@administrative_role_required
def shipment_create(request):
    shipment = Shipment()
    if request.method == "POST":
        form = ShipmentForm(request.POST, instance=shipment)
        formset = PackageFormSet(request.POST, instance=shipment, prefix="packages")
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                registered = ShipmentStatus.objects.get(code="REGISTERED")
                shipment = form.save(commit=False)
                shipment.current_status = registered
                shipment.current_agency = shipment.origin
                shipment.created_by = request.user
                shipment.updated_by = request.user
                shipment.save()
                formset.instance = shipment
                formset.save()
                TrackingEvent.objects.create(
                    shipment=shipment,
                    status=registered,
                    agency=shipment.origin,
                    notes="Envío registrado y recibido en ventanilla.",
                    created_by=request.user,
                    is_system=True,
                )
            messages.success(request, f"Envío {shipment.order_number} registrado correctamente.")
            return redirect("shipment_detail", pk=shipment.pk)
    else:
        form = ShipmentForm(
            instance=shipment,
            initial={"payment_status": Shipment.PaymentStatus.PENDING, "insurance_cost": 0, "discount": 0},
        )
        formset = PackageFormSet(instance=shipment, prefix="packages")
    return render(
        request,
        "shipments/shipment_form.html",
        {"form": form, "formset": formset, "title": "Registrar envío", "section": "shipments"},
    )


@administrative_role_required
def shipment_update(request, pk):
    shipment = get_object_or_404(Shipment.objects.select_related("current_status"), pk=pk)
    if not shipment.can_edit:
        messages.error(request, "Solo se pueden editar envíos que aún están en estado Registrado.")
        return redirect("shipment_detail", pk=shipment.pk)
    if request.method == "POST":
        form = ShipmentForm(request.POST, instance=shipment)
        formset = PackageFormSet(request.POST, instance=shipment, prefix="packages")
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                shipment = form.save(commit=False)
                shipment.updated_by = request.user
                shipment.save()
                formset.save()
            messages.success(request, f"Envío {shipment.order_number} actualizado.")
            return redirect("shipment_detail", pk=shipment.pk)
    else:
        form = ShipmentForm(instance=shipment)
        formset = PackageFormSet(instance=shipment, prefix="packages")
    return render(
        request,
        "shipments/shipment_form.html",
        {"form": form, "formset": formset, "title": f"Editar {shipment.order_number}", "shipment": shipment, "section": "shipments"},
    )


@admin_role_required
def shipment_cancel(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    shipment = get_object_or_404(Shipment.objects.select_related("current_status", "origin"), pk=pk)
    from operations.models import Incident

    form = CancellationForm(request.POST)
    if shipment.current_status.is_terminal:
        messages.error(request, "El envío ya se encuentra en un estado final y no puede anularse.")
    elif Incident.objects.filter(shipment=shipment).exclude(status=Incident.Status.RESOLVED).exists():
        messages.error(request, "Primero debes resolver la incidencia activa antes de anular el envío.")
    elif form.is_valid():
        with transaction.atomic():
            canceled = ShipmentStatus.objects.get(code="CANCELED")
            previous_status = shipment.current_status
            shipment.current_status = canceled
            shipment.status_changed_at = timezone.now()
            shipment.cancel_reason = form.cleaned_data["reason"]
            shipment.updated_by = request.user
            shipment.save(validate=False)
            TrackingEvent.objects.create(
                shipment=shipment,
                previous_status=previous_status,
                status=canceled,
                agency=shipment.origin,
                notes=form.cleaned_data["reason"],
                created_by=request.user,
            )
        messages.success(request, f"Envío {shipment.order_number} anulado.")
    else:
        messages.error(request, "El motivo de anulación debe tener al menos 10 caracteres.")
    return redirect("shipment_detail", pk=shipment.pk)


@login_required
def shipment_ticket(request, pk):
    shipment = get_object_or_404(
        Shipment.objects.select_related("sender", "recipient", "origin", "destination", "current_status", "created_by").prefetch_related("packages"),
        pk=pk,
    )
    public_url = request.build_absolute_uri(
        f"{reverse('public_tracking')}?order={shipment.order_number}&code={shipment.tracking_code}"
    )
    payload = public_url
    qr = qrcode.QRCode(version=2, box_size=7, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    image = qr.make_image(fill_color="#102746", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    qr_data = base64.b64encode(buffer.getvalue()).decode("ascii")
    return render(
        request,
        "shipments/shipment_ticket.html",
        {"shipment": shipment, "qr_data": qr_data, "section": "shipments"},
    )


@admin_role_required
def agency_list(request):
    agencies = Agency.objects.all()
    return render(request, "shipments/agency_list.html", {"agencies": agencies, "section": "agencies"})


@admin_role_required
def agency_create(request):
    if request.method == "POST":
        form = AgencyForm(request.POST)
        if form.is_valid():
            agency = form.save()
            messages.success(request, f"Agencia {agency.name} creada.")
            return redirect("agency_list")
    else:
        form = AgencyForm(initial={"is_active": True, "supports_ground": True})
    return render(request, "shipments/agency_form.html", {"form": form, "title": "Nueva agencia", "section": "agencies"})


@admin_role_required
def agency_update(request, pk):
    agency = get_object_or_404(Agency, pk=pk)
    if request.method == "POST":
        form = AgencyForm(request.POST, instance=agency)
        if form.is_valid():
            form.save()
            messages.success(request, f"Agencia {agency.name} actualizada.")
            return redirect("agency_list")
    else:
        form = AgencyForm(instance=agency)
    return render(request, "shipments/agency_form.html", {"form": form, "title": f"Editar {agency.name}", "agency": agency, "section": "agencies"})


@admin_role_required
def agency_toggle_active(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    agency = get_object_or_404(Agency, pk=pk)
    agency.is_active = not agency.is_active
    agency.save(update_fields=["is_active", "updated_at"])
    messages.success(request, f"Agencia {agency.name} {'activada' if agency.is_active else 'desactivada'}.")
    return redirect("agency_list")
