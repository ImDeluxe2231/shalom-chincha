from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from shipments.models import Shipment, ShipmentStatus, TrackingEvent

from .models import Delivery, Incident, IncidentAction


@transaction.atomic
def complete_delivery(*, shipment_id, delivery, user):
    shipment = Shipment.objects.select_for_update().select_related(
        "current_status", "destination", "recipient"
    ).prefetch_related("packages").get(pk=shipment_id)
    if shipment.current_status.code != "READY_PICKUP":
        raise ValidationError("El envío debe estar disponible para recojo antes de entregarse.")
    if Incident.objects.filter(shipment=shipment).exclude(status=Incident.Status.RESOLVED).exists():
        raise ValidationError("Resuelve la incidencia activa antes de completar la entrega.")
    if hasattr(shipment, "delivery"):
        raise ValidationError("Este envío ya tiene una entrega registrada.")

    previous_status = shipment.current_status
    delivered_status = ShipmentStatus.objects.get(code="DELIVERED")
    delivery.shipment = shipment
    delivery.agency = shipment.destination
    delivery.packages_delivered = shipment.total_packages
    delivery.payment_confirmed = True
    delivery.delivered_by = user
    delivery.delivered_at = timezone.now()
    delivery.save()

    shipment.current_status = delivered_status
    shipment.current_agency = shipment.destination
    shipment.current_location = None
    shipment.payment_status = Shipment.PaymentStatus.PAID
    shipment.status_changed_at = delivery.delivered_at
    shipment.updated_by = user
    shipment.save(validate=False)
    TrackingEvent.objects.create(
        shipment=shipment,
        previous_status=previous_status,
        status=delivered_status,
        agency=shipment.destination,
        notes=f"Entrega confirmada a {delivery.receiver_name}.",
        created_by=user,
        visible_to_customer=True,
    )
    return delivery


@transaction.atomic
def report_incident(*, shipment_id, incident, user):
    shipment = Shipment.objects.select_for_update().select_related(
        "current_status", "current_agency", "origin"
    ).get(pk=shipment_id)
    if shipment.current_status.is_terminal:
        raise ValidationError("No se pueden reportar incidencias en un envío finalizado.")
    if shipment.current_status.code == "INCIDENT" or Incident.objects.filter(
        shipment=shipment
    ).exclude(status=Incident.Status.RESOLVED).exists():
        raise ValidationError("El envío ya tiene una incidencia activa.")

    previous_status = shipment.current_status
    incident_status = ShipmentStatus.objects.get(code="INCIDENT")
    incident.shipment = shipment
    incident.previous_status = previous_status
    incident.reported_by = user
    incident.status = Incident.Status.OPEN
    incident.save()
    IncidentAction.objects.create(
        incident=incident,
        action=IncidentAction.Action.REPORTED,
        notes=f"Reporte creado con gravedad {incident.get_severity_display()} en {incident.agency.name}.",
        performed_by=user,
    )

    shipment.current_status = incident_status
    shipment.status_changed_at = timezone.now()
    shipment.updated_by = user
    shipment.save(validate=False)
    TrackingEvent.objects.create(
        shipment=shipment,
        previous_status=previous_status,
        status=incident_status,
        agency=incident.agency,
        notes=f"Incidencia {incident.code}: {incident.get_incident_type_display()}.",
        created_by=user,
        visible_to_customer=True,
    )
    return incident


@transaction.atomic
def review_incident(*, incident_id, assigned_to, public_message, user):
    incident = Incident.objects.select_for_update().get(pk=incident_id)
    if incident.status == Incident.Status.RESOLVED:
        raise ValidationError("La incidencia ya fue resuelta.")
    incident.assigned_to = assigned_to
    incident.public_message = public_message.strip()
    incident.status = Incident.Status.IN_REVIEW
    incident.save()
    IncidentAction.objects.create(
        incident=incident,
        action=IncidentAction.Action.ASSIGNED,
        notes=f"Incidencia asignada a {assigned_to.display_name} para su revisión.",
        performed_by=user,
    )
    return incident


@transaction.atomic
def resolve_incident(*, incident_id, resolution, public_message, user):
    incident = Incident.objects.select_for_update().select_related(
        "shipment", "previous_status", "agency"
    ).get(pk=incident_id)
    shipment = Shipment.objects.select_for_update().select_related("current_status").get(pk=incident.shipment_id)
    if incident.status == Incident.Status.RESOLVED:
        raise ValidationError("La incidencia ya fue resuelta.")
    if shipment.current_status.code != "INCIDENT":
        raise ValidationError("El envío ya no se encuentra detenido por esta incidencia.")

    incident.status = Incident.Status.RESOLVED
    incident.resolution = resolution.strip()
    incident.public_message = public_message.strip()
    incident.resolved_by = user
    incident.resolved_at = timezone.now()
    if incident.assigned_to_id is None:
        incident.assigned_to = user
    incident.save()
    IncidentAction.objects.create(
        incident=incident,
        action=IncidentAction.Action.RESOLVED,
        notes=resolution.strip(),
        performed_by=user,
    )

    interrupted_status = shipment.current_status
    shipment.current_status = incident.previous_status
    shipment.status_changed_at = incident.resolved_at
    shipment.updated_by = user
    shipment.save(validate=False)
    TrackingEvent.objects.create(
        shipment=shipment,
        previous_status=interrupted_status,
        status=incident.previous_status,
        agency=incident.agency,
        notes=f"Incidencia {incident.code} resuelta. El envío retoma su operación.",
        created_by=user,
        visible_to_customer=True,
    )
    return incident
