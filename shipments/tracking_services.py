from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Shipment, ShipmentStatus, TrackingEvent


TRANSITIONS = {
    "REGISTERED": "RECEIVED",
    "RECEIVED": "IN_WAREHOUSE",
    "IN_WAREHOUSE": "DISPATCHED",
    "DISPATCHED": "IN_TRANSIT",
    "IN_TRANSIT": "AT_DESTINATION",
    "AT_DESTINATION": "READY_PICKUP",
}

ACTION_LABELS = {
    "RECEIVED": "Confirmar recepción física",
    "IN_WAREHOUSE": "Ingresar al almacén",
    "DISPATCHED": "Registrar despacho",
    "IN_TRANSIT": "Iniciar tránsito",
    "AT_DESTINATION": "Confirmar recepción en destino",
    "READY_PICKUP": "Habilitar para recojo",
}

ACTION_DESCRIPTIONS = {
    "RECEIVED": "Verifica que todos los bultos hayan sido recibidos en la agencia de origen.",
    "IN_WAREHOUSE": "Asigna una ubicación física dentro del almacén de origen.",
    "DISPATCHED": "Registra el manifiesto, vehículo o vuelo utilizado para la salida.",
    "IN_TRANSIT": "Confirma que la unidad se encuentra viajando hacia el destino.",
    "AT_DESTINATION": "Verifica la llegada y asigna una ubicación en el almacén de destino.",
    "READY_PICKUP": "Confirma que el envío está preparado para ser recogido.",
}


def transition_context(shipment):
    target_code = TRANSITIONS.get(shipment.current_status.code)
    if not target_code:
        return None
    status = ShipmentStatus.objects.get(code=target_code)
    return {
        "code": target_code,
        "status": status,
        "label": ACTION_LABELS[target_code],
        "description": ACTION_DESCRIPTIONS[target_code],
    }


@transaction.atomic
def register_transition(*, shipment_id, target_code, user, location=None, transport_reference="", notes=""):
    shipment = Shipment.objects.select_for_update().select_related(
        "current_status", "origin", "destination", "current_location"
    ).get(pk=shipment_id)
    expected_code = TRANSITIONS.get(shipment.current_status.code)
    if target_code != expected_code:
        raise ValidationError("El estado del envío cambió o la transición solicitada no está permitida.")

    previous_status = shipment.current_status
    target_status = ShipmentStatus.objects.get(code=target_code)
    event_agency = shipment.destination if target_code in {"AT_DESTINATION", "READY_PICKUP"} else shipment.origin

    if target_code in {"IN_WAREHOUSE", "AT_DESTINATION"}:
        if location is None:
            raise ValidationError("Selecciona una ubicación de almacén.")
        if location.agency_id != event_agency.id or not location.is_active:
            raise ValidationError("La ubicación seleccionada no pertenece a la agencia correspondiente.")
    if target_code == "DISPATCHED" and not transport_reference.strip():
        raise ValidationError("Ingresa la referencia del manifiesto, vehículo o vuelo.")

    if target_code in {"DISPATCHED", "IN_TRANSIT"}:
        shipment.current_location = None
    elif location is not None:
        shipment.current_location = location
    shipment.current_agency = event_agency
    shipment.current_status = target_status
    shipment.status_changed_at = timezone.now()
    shipment.updated_by = user
    # La ruta fue validada al registrar la orden. Un cambio posterior en la
    # ficha del cliente o catálogo de agencias no debe bloquear la trazabilidad.
    shipment.save(validate=False)

    return TrackingEvent.objects.create(
        shipment=shipment,
        previous_status=previous_status,
        status=target_status,
        agency=event_agency,
        location=location,
        transport_reference=transport_reference.strip(),
        notes=notes.strip() or target_status.description,
        created_by=user,
        visible_to_customer=True,
    )
