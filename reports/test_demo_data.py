from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from customers.models import Customer
from operations.models import Delivery, Incident
from shipments.models import Shipment, TrackingEvent

from .management.commands.cargar_datos_demo import DEMO_MARKER


class MassiveDemoDataCommandTests(TestCase):
    def test_command_creates_realistic_data_and_is_idempotent(self):
        output = StringIO()
        call_command(
            "cargar_datos_demo", clientes=30, envios=36, dias=60,
            semilla=2027, stdout=output,
        )
        self.assertEqual(Customer.objects.filter(notes__contains=DEMO_MARKER).count(), 30)
        self.assertEqual(Shipment.objects.filter(notes__contains=DEMO_MARKER).count(), 36)
        self.assertGreaterEqual(Delivery.objects.filter(notes__contains=DEMO_MARKER).count(), 8)
        self.assertGreaterEqual(Incident.objects.filter(description__contains=DEMO_MARKER).count(), 3)
        self.assertGreater(TrackingEvent.objects.filter(shipment__notes__contains=DEMO_MARKER).count(), 80)
        self.assertGreater(
            Shipment.objects.filter(notes__contains=DEMO_MARKER).dates("created_at", "day").count(), 10
        )

        admin = User.objects.get(role=User.Role.ADMIN)
        self.client.force_login(admin)
        dashboard = self.client.get(reverse("dashboard"))
        self.assertContains(dashboard, "Envíos registrados")
        self.assertContains(dashboard, "Incidencias activas")

        first_count = Shipment.objects.count()
        second_output = StringIO()
        call_command(
            "cargar_datos_demo", clientes=30, envios=36, dias=60,
            semilla=2027, stdout=second_output,
        )
        self.assertEqual(Shipment.objects.count(), first_count)
        self.assertIn("No se duplicaron datos", second_output.getvalue())
