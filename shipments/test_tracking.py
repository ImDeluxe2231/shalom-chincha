from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from customers.models import Customer

from .models import Agency, Package, Shipment, ShipmentStatus, TrackingEvent, WarehouseLocation
from .tracking_services import register_transition


class TrackingModuleTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="track_admin", password="Prueba2027!", role=User.Role.ADMIN)
        self.office = User.objects.create_user(username="track_office", password="Prueba2027!", role=User.Role.ADMINISTRATIVE)
        self.operator = User.objects.create_user(username="track_operator", password="Prueba2027!", role=User.Role.OPERATIONAL)
        self.sender = Customer.objects.create(
            customer_type="PERSON", document_type="DNI", document_number="71111111",
            first_name="Rosa", last_name="Salas", phone="911111111", district="Chincha Alta",
            address="Calle Origen 100", created_by=self.admin, updated_by=self.admin,
        )
        self.recipient = Customer.objects.create(
            customer_type="PERSON", document_type="DNI", document_number="72222222",
            first_name="Marco", last_name="León", phone="922222222", district="La Victoria",
            province="Lima", department="Lima", address="Calle Destino 200",
            created_by=self.admin, updated_by=self.admin,
        )
        self.origin = Agency.objects.get(code="CHI")
        self.destination = Agency.objects.get(code="LIM")
        self.origin_location = WarehouseLocation.objects.get(agency=self.origin, code="ALM-01")
        self.destination_location = WarehouseLocation.objects.get(agency=self.destination, code="ALM-01")
        registered = ShipmentStatus.objects.get(code="REGISTERED")
        self.shipment = Shipment.objects.create(
            sender=self.sender, recipient=self.recipient, origin=self.origin, destination=self.destination,
            current_agency=self.origin, transport_mode="GROUND", service_type="AGENCY", payer="SENDER",
            payment_timing="ORIGIN", payment_status="PAID", shipping_cost=Decimal("28.00"),
            current_status=registered, created_by=self.admin, updated_by=self.admin,
        )
        Package.objects.create(
            shipment=self.shipment, description="Caja de prueba", quantity=1, weight=Decimal("3.00"),
            length=Decimal("30"), width=Decimal("20"), height=Decimal("20"),
        )
        self.initial_event = TrackingEvent.objects.create(
            shipment=self.shipment, status=registered, agency=self.origin,
            notes="Envío registrado", created_by=self.admin, is_system=True,
        )

    def advance(self, target_code, location=None, reference=""):
        register_transition(
            shipment_id=self.shipment.pk, target_code=target_code, user=self.operator,
            location=location, transport_reference=reference,
        )
        self.shipment.refresh_from_db()

    def test_operator_completes_valid_operational_sequence(self):
        self.advance("RECEIVED")
        self.advance("IN_WAREHOUSE", self.origin_location)
        self.advance("DISPATCHED", reference="MAN-2027-001")
        self.advance("IN_TRANSIT")
        self.advance("AT_DESTINATION", self.destination_location)
        self.advance("READY_PICKUP")
        self.assertEqual(self.shipment.current_status.code, "READY_PICKUP")
        self.assertEqual(self.shipment.current_agency, self.destination)
        self.assertEqual(self.shipment.tracking_events.count(), 7)

    def test_invalid_state_jump_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.advance("IN_TRANSIT")
        self.shipment.refresh_from_db()
        self.assertEqual(self.shipment.current_status.code, "REGISTERED")

    def test_warehouse_transition_requires_matching_location(self):
        self.advance("RECEIVED")
        with self.assertRaises(ValidationError):
            self.advance("IN_WAREHOUSE", self.destination_location)

    def test_dispatch_requires_transport_reference(self):
        self.advance("RECEIVED")
        self.advance("IN_WAREHOUSE", self.origin_location)
        with self.assertRaises(ValidationError):
            self.advance("DISPATCHED")

    def test_administrative_user_cannot_update_operational_status(self):
        self.client.force_login(self.office)
        response = self.client.post(reverse("tracking_transition", args=[self.shipment.pk, "RECEIVED"]), {"notes": "Recepción"})
        self.assertEqual(response.status_code, 403)

    def test_operator_updates_status_from_interface(self):
        self.client.force_login(self.operator)
        response = self.client.post(reverse("tracking_transition", args=[self.shipment.pk, "RECEIVED"]), {"notes": "Bultos conformes"})
        self.assertRedirects(response, reverse("tracking_detail", args=[self.shipment.pk]))
        self.shipment.refresh_from_db()
        self.assertEqual(self.shipment.current_status.code, "RECEIVED")
        self.assertEqual(self.shipment.tracking_events.last().previous_status.code, "REGISTERED")

    def test_tracking_continues_if_customer_was_later_deactivated(self):
        self.sender.is_active = False
        self.sender.save(update_fields=["is_active"])
        self.advance("RECEIVED")
        self.assertEqual(self.shipment.current_status.code, "RECEIVED")

    def test_tracking_event_is_immutable(self):
        self.initial_event.notes = "Intento de modificación"
        with self.assertRaises(ValidationError):
            self.initial_event.save()
        with self.assertRaises(ValidationError):
            self.initial_event.delete()

    def test_public_tracking_requires_matching_order_and_code(self):
        response = self.client.post(reverse("public_tracking"), {
            "order_number": self.shipment.order_number,
            "tracking_code": self.shipment.tracking_code,
        })
        self.assertContains(response, self.shipment.order_number)
        self.assertContains(response, "Envío registrado en ventanilla")
        self.assertNotContains(response, self.sender.phone)
        self.assertNotContains(response, "Caja de prueba")

    def test_public_tracking_rejects_wrong_code_without_disclosing_data(self):
        response = self.client.post(reverse("public_tracking"), {
            "order_number": self.shipment.order_number,
            "tracking_code": "999999",
        })
        self.assertContains(response, "No encontramos un envío")
        self.assertNotContains(response, self.recipient.display_name)

    def test_admin_manages_warehouse_locations(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("warehouse_location_create"), {
            "agency": self.origin.pk, "code": "Z-B02", "name": "Zona B",
            "zone": "B", "rack": "02", "level": "Nivel 2", "is_active": "on",
        })
        self.assertRedirects(response, reverse("warehouse_location_list"))
        self.assertTrue(WarehouseLocation.objects.filter(agency=self.origin, code="Z-B02").exists())
