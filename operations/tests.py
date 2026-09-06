from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from customers.models import Customer
from shipments.models import Agency, Package, Shipment, ShipmentStatus, TrackingEvent

from .forms import IncidentForm
from .models import Delivery, Incident, IncidentAction
from .services import complete_delivery, report_incident, resolve_incident, review_incident


class OperationsModuleTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="ops_admin", password="Prueba2027!", role=User.Role.ADMIN)
        self.office = User.objects.create_user(username="ops_office", password="Prueba2027!", role=User.Role.ADMINISTRATIVE)
        self.operator = User.objects.create_user(username="ops_worker", password="Prueba2027!", role=User.Role.OPERATIONAL)
        self.sender = Customer.objects.create(
            customer_type="PERSON", document_type="DNI", document_number="73333333",
            first_name="Lucía", last_name="Campos", phone="933333333", district="Chincha Alta",
            address="Av. Principal 100", created_by=self.admin, updated_by=self.admin,
        )
        self.recipient = Customer.objects.create(
            customer_type="PERSON", document_type="DNI", document_number="74444444",
            first_name="Diego", last_name="Rojas", phone="944444444", district="La Victoria",
            province="Lima", department="Lima", address="Jr. Destino 200",
            created_by=self.admin, updated_by=self.admin,
        )
        self.origin = Agency.objects.get(code="CHI")
        self.destination = Agency.objects.get(code="LIM")

    def create_shipment(self, status_code="READY_PICKUP", payment_status="PENDING"):
        status = ShipmentStatus.objects.get(code=status_code)
        shipment = Shipment.objects.create(
            sender=self.sender, recipient=self.recipient, origin=self.origin, destination=self.destination,
            current_agency=self.destination if status_code in {"READY_PICKUP", "DELIVERED"} else self.origin,
            transport_mode="GROUND", service_type="AGENCY", payer="RECIPIENT",
            payment_timing="DESTINATION", payment_status=payment_status,
            shipping_cost=Decimal("30.00"), current_status=status,
            created_by=self.admin, updated_by=self.operator,
        )
        Package.objects.create(
            shipment=shipment, description="Caja sellada", quantity=2, weight=Decimal("2.00"),
            length=Decimal("30"), width=Decimal("20"), height=Decimal("15"),
        )
        TrackingEvent.objects.create(
            shipment=shipment, status=status,
            agency=self.destination if status_code == "READY_PICKUP" else self.origin,
            notes="Estado para pruebas", created_by=self.operator,
        )
        return shipment

    def delivery_data(self, shipment):
        return {
            "delivery_method": "AGENCY",
            "receiver_type": "RECIPIENT",
            "receiver_name": self.recipient.display_name,
            "receiver_document_type": "DNI",
            "receiver_document_number": self.recipient.document_number,
            "receiver_phone": self.recipient.phone,
            "relationship": "",
            "verification_method": "DOCUMENT_CODE",
            "package_condition": "CONFORMING",
            "condition_notes": "",
            "notes": "Entrega de prueba",
            "tracking_code_confirmation": shipment.tracking_code,
            "confirm_payment": "on",
            "acceptance": "on",
        }

    def create_incident(self, shipment):
        incident = Incident(
            agency=shipment.current_agency or shipment.origin,
            incident_type=Incident.IncidentType.DELAY,
            severity=Incident.Severity.HIGH,
            description="La unidad presentó una demora operativa durante el traslado.",
            public_message="El envío presenta una demora y está siendo revisado.",
        )
        return report_incident(shipment_id=shipment.pk, incident=incident, user=self.operator)

    def test_administrative_user_completes_delivery_and_closes_shipment(self):
        shipment = self.create_shipment()
        self.client.force_login(self.office)
        response = self.client.post(reverse("delivery_create", args=[shipment.pk]), self.delivery_data(shipment))
        delivery = Delivery.objects.get(shipment=shipment)
        self.assertRedirects(response, reverse("delivery_detail", args=[delivery.pk]))
        shipment.refresh_from_db()
        self.assertEqual(shipment.current_status.code, "DELIVERED")
        self.assertEqual(shipment.payment_status, "PAID")
        self.assertEqual(delivery.packages_delivered, 2)
        self.assertEqual(shipment.tracking_events.last().previous_status.code, "READY_PICKUP")

    def test_wrong_tracking_code_prevents_delivery(self):
        shipment = self.create_shipment()
        data = self.delivery_data(shipment)
        data["tracking_code_confirmation"] = "999999"
        self.client.force_login(self.office)
        response = self.client.post(reverse("delivery_create", args=[shipment.pk]), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "El código no coincide")
        self.assertFalse(Delivery.objects.filter(shipment=shipment).exists())

    def test_delivery_requires_payment_confirmation(self):
        shipment = self.create_shipment(payment_status="PENDING")
        data = self.delivery_data(shipment)
        data.pop("confirm_payment")
        self.client.force_login(self.office)
        response = self.client.post(reverse("delivery_create", args=[shipment.pk]), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Delivery.objects.filter(shipment=shipment).exists())

    def test_delivery_receipt_contains_qr(self):
        shipment = self.create_shipment(payment_status="PAID")
        self.client.force_login(self.office)
        self.client.post(reverse("delivery_create", args=[shipment.pk]), self.delivery_data(shipment))
        delivery = Delivery.objects.get(shipment=shipment)
        response = self.client.get(reverse("delivery_receipt", args=[delivery.pk]))
        self.assertContains(response, "data:image/png;base64,")
        self.assertContains(response, str(delivery.verification_code))

    def test_public_verification_masks_personal_data(self):
        shipment = self.create_shipment(payment_status="PAID")
        self.client.force_login(self.office)
        self.client.post(reverse("delivery_create", args=[shipment.pk]), self.delivery_data(shipment))
        self.client.logout()
        delivery = Delivery.objects.get(shipment=shipment)
        response = self.client.get(reverse("delivery_verify", args=[delivery.verification_code]))
        self.assertContains(response, "Entrega verificada")
        self.assertContains(response, delivery.masked_document)
        self.assertNotContains(response, delivery.receiver_document_number)
        self.assertNotContains(response, delivery.receiver_name)

    def test_delivery_record_is_immutable(self):
        shipment = self.create_shipment(payment_status="PAID")
        self.client.force_login(self.office)
        self.client.post(reverse("delivery_create", args=[shipment.pk]), self.delivery_data(shipment))
        delivery = Delivery.objects.get(shipment=shipment)
        delivery.notes = "Intento de cambio"
        with self.assertRaises(ValidationError):
            delivery.save()
        with self.assertRaises(ValidationError):
            delivery.delete()

    def test_incident_suspends_shipment_and_creates_audit_action(self):
        shipment = self.create_shipment(status_code="IN_TRANSIT")
        incident = self.create_incident(shipment)
        shipment.refresh_from_db()
        self.assertEqual(shipment.current_status.code, "INCIDENT")
        self.assertEqual(incident.previous_status.code, "IN_TRANSIT")
        self.assertEqual(incident.actions.get().action, IncidentAction.Action.REPORTED)

    def test_second_active_incident_is_rejected(self):
        shipment = self.create_shipment(status_code="IN_TRANSIT")
        self.create_incident(shipment)
        with self.assertRaises(ValidationError):
            self.create_incident(shipment)

    def test_admin_reviews_and_resolves_incident_restoring_previous_status(self):
        shipment = self.create_shipment(status_code="IN_TRANSIT")
        incident = self.create_incident(shipment)
        review_incident(
            incident_id=incident.pk, assigned_to=self.operator,
            public_message="El caso está siendo atendido.", user=self.admin,
        )
        resolve_incident(
            incident_id=incident.pk,
            resolution="Se reasignó la unidad y se verificó la integridad de los bultos.",
            public_message="La incidencia fue resuelta y el envío continúa.", user=self.admin,
        )
        incident.refresh_from_db()
        shipment.refresh_from_db()
        self.assertEqual(incident.status, Incident.Status.RESOLVED)
        self.assertEqual(shipment.current_status.code, "IN_TRANSIT")
        self.assertEqual(incident.actions.count(), 3)

    def test_non_admin_cannot_resolve_incident(self):
        shipment = self.create_shipment(status_code="IN_TRANSIT")
        incident = self.create_incident(shipment)
        self.client.force_login(self.operator)
        response = self.client.post(reverse("incident_resolve", args=[incident.pk]), {
            "resolution": "Solución válida registrada por prueba.",
            "resume_confirmation": "on",
        })
        self.assertEqual(response.status_code, 403)

    def test_terminal_shipment_rejects_incident(self):
        shipment = self.create_shipment(status_code="DELIVERED", payment_status="PAID")
        with self.assertRaises(ValidationError):
            self.create_incident(shipment)

    def test_incident_form_rejects_unsafe_evidence_extension(self):
        shipment = self.create_shipment(status_code="IN_TRANSIT")
        uploaded = SimpleUploadedFile("archivo.exe", b"contenido", content_type="application/octet-stream")
        form = IncidentForm({
            "agency": self.origin.pk,
            "incident_type": "DAMAGE",
            "severity": "HIGH",
            "description": "Se detectó una observación visible en el embalaje.",
            "public_message": "El envío está siendo revisado.",
        }, {"evidence": uploaded}, shipment=shipment)
        self.assertFalse(form.is_valid())
        self.assertIn("evidence", form.errors)

    def test_incident_evidence_route_requires_login(self):
        shipment = self.create_shipment(status_code="IN_TRANSIT")
        incident = self.create_incident(shipment)
        response = self.client.get(reverse("incident_evidence", args=[incident.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_active_incident_prevents_shipment_cancellation(self):
        shipment = self.create_shipment(status_code="IN_TRANSIT")
        self.create_incident(shipment)
        self.client.force_login(self.admin)
        self.client.post(reverse("shipment_cancel", args=[shipment.pk]), {"reason": "Solicitud administrativa válida"})
        shipment.refresh_from_db()
        self.assertEqual(shipment.current_status.code, "INCIDENT")

    def test_public_tracking_shows_safe_incident_message(self):
        shipment = self.create_shipment(status_code="IN_TRANSIT")
        self.create_incident(shipment)
        response = self.client.post(reverse("public_tracking"), {
            "order_number": shipment.order_number,
            "tracking_code": shipment.tracking_code,
        })
        self.assertContains(response, "El envío presenta una demora")
        self.assertNotContains(response, "La unidad presentó una demora operativa")

    def test_incident_form_rejects_personal_data_in_public_message(self):
        shipment = self.create_shipment(status_code="IN_TRANSIT")
        form = IncidentForm({
            "agency": self.origin.pk,
            "incident_type": "DELAY",
            "severity": "MEDIUM",
            "description": "Descripción interna suficientemente detallada.",
            "public_message": "Contactar al teléfono 944444444 para coordinar.",
        }, shipment=shipment)
        self.assertFalse(form.is_valid())
        self.assertIn("public_message", form.errors)
