from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from customers.models import Customer

from .models import Agency, Package, Shipment, ShipmentStatus, TrackingEvent


class ShipmentTestBase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="shipment_admin", password="Prueba2027!", role=User.Role.ADMIN)
        self.office = User.objects.create_user(username="shipment_office", password="Prueba2027!", role=User.Role.ADMINISTRATIVE)
        self.operator = User.objects.create_user(username="shipment_operator", password="Prueba2027!", role=User.Role.OPERATIONAL)
        self.sender = Customer.objects.create(
            customer_type="PERSON", document_type="DNI", document_number="70001111",
            first_name="Ana", last_name="Ramos", phone="911222333", district="Chincha Alta",
            address="Av. Uno 100", created_by=self.admin, updated_by=self.admin,
        )
        self.recipient = Customer.objects.create(
            customer_type="PERSON", document_type="DNI", document_number="70002222",
            first_name="Luis", last_name="Torres", phone="922333444", district="La Victoria",
            province="Lima", department="Lima", address="Av. Dos 200",
            created_by=self.admin, updated_by=self.admin,
        )
        self.origin = Agency.objects.get(code="CHI")
        self.destination = Agency.objects.get(code="LIM")
        self.registered = ShipmentStatus.objects.get(code="REGISTERED")

    def create_shipment(self):
        shipment = Shipment.objects.create(
            sender=self.sender, recipient=self.recipient, origin=self.origin, destination=self.destination,
            transport_mode="GROUND", service_type="AGENCY", payer="SENDER", payment_timing="ORIGIN",
            payment_status="PAID", shipping_cost=Decimal("20.00"), insurance_cost=Decimal("2.00"),
            discount=Decimal("1.00"), current_status=self.registered,
            current_agency=self.origin,
            created_by=self.admin, updated_by=self.admin,
        )
        Package.objects.create(
            shipment=shipment, package_type="PACKAGE", description="Ropa", quantity=2,
            weight=Decimal("2.00"), length=Decimal("30"), width=Decimal("20"), height=Decimal("10"),
            declared_value=Decimal("100.00"),
        )
        TrackingEvent.objects.create(
            shipment=shipment, status=self.registered, agency=self.origin,
            notes="Registro inicial", created_by=self.admin, is_system=True,
        )
        return shipment


class ShipmentModelTests(ShipmentTestBase):
    def test_generates_order_and_tracking_code(self):
        shipment = self.create_shipment()
        self.assertTrue(shipment.order_number.startswith(f"CHI-{timezone.localdate().year}-"))
        self.assertEqual(len(shipment.tracking_code), 6)
        self.assertTrue(shipment.tracking_code.isdigit())

    def test_sequences_are_consecutive(self):
        first = self.create_shipment()
        second = self.create_shipment()
        first_number = int(first.order_number.rsplit("-", 1)[1])
        second_number = int(second.order_number.rsplit("-", 1)[1])
        self.assertEqual(second_number, first_number + 1)

    def test_cost_and_package_totals(self):
        shipment = self.create_shipment()
        self.assertEqual(shipment.total_cost, Decimal("21.00"))
        self.assertEqual(shipment.total_packages, 2)
        self.assertEqual(shipment.total_actual_weight, Decimal("4.00"))


class ShipmentViewTests(ShipmentTestBase):
    def form_data(self):
        return {
            "sender": self.sender.pk,
            "recipient": self.recipient.pk,
            "origin": self.origin.pk,
            "destination": self.destination.pk,
            "transport_mode": "GROUND",
            "service_type": "AGENCY",
            "payer": "SENDER",
            "payment_timing": "ORIGIN",
            "payment_status": "PAID",
            "shipping_cost": "25.00",
            "insurance_cost": "2.50",
            "discount": "0.00",
            "estimated_delivery_date": (timezone.localdate() + timedelta(days=2)).isoformat(),
            "notes": "Prueba completa",
            "packages-TOTAL_FORMS": "1",
            "packages-INITIAL_FORMS": "0",
            "packages-MIN_NUM_FORMS": "1",
            "packages-MAX_NUM_FORMS": "1000",
            "packages-0-package_type": "PACKAGE",
            "packages-0-description": "Documentos y prendas",
            "packages-0-quantity": "1",
            "packages-0-weight": "2.50",
            "packages-0-length": "35",
            "packages-0-width": "25",
            "packages-0-height": "20",
            "packages-0-declared_value": "150.00",
            "packages-0-is_fragile": "",
            "packages-0-observations": "",
        }

    def test_administrative_creates_complete_shipment(self):
        self.client.force_login(self.office)
        response = self.client.post(reverse("shipment_create"), self.form_data())
        shipment = Shipment.objects.get(notes="Prueba completa")
        self.assertRedirects(response, reverse("shipment_detail", args=[shipment.pk]))
        self.assertEqual(shipment.packages.count(), 1)
        self.assertEqual(shipment.tracking_events.count(), 1)
        self.assertEqual(shipment.current_status.code, "REGISTERED")
        self.assertEqual(shipment.current_agency, self.origin)

    def test_operator_can_view_but_cannot_create(self):
        shipment = self.create_shipment()
        self.client.force_login(self.operator)
        self.assertEqual(self.client.get(reverse("shipment_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("shipment_detail", args=[shipment.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("shipment_create")).status_code, 403)

    def test_admin_can_cancel_shipment_and_creates_event(self):
        shipment = self.create_shipment()
        self.client.force_login(self.admin)
        self.client.post(reverse("shipment_cancel", args=[shipment.pk]), {"reason": "Error confirmado en los datos"})
        shipment.refresh_from_db()
        self.assertEqual(shipment.current_status.code, "CANCELED")
        self.assertEqual(shipment.tracking_events.last().status.code, "CANCELED")

    def test_ticket_contains_order_and_qr(self):
        shipment = self.create_shipment()
        self.client.force_login(self.operator)
        response = self.client.get(reverse("shipment_ticket", args=[shipment.pk]))
        self.assertContains(response, shipment.order_number)
        self.assertContains(response, "data:image/png;base64,")

    def test_shipment_requires_at_least_one_package(self):
        self.client.force_login(self.office)
        data = self.form_data()
        data["packages-TOTAL_FORMS"] = "0"
        response = self.client.post(reverse("shipment_create"), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "al menos un paquete")
