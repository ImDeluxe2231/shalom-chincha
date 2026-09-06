from datetime import timedelta
from decimal import Decimal
from zipfile import ZipFile
from io import BytesIO

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from customers.models import Customer
from operations.models import Delivery, Incident
from operations.services import complete_delivery, report_incident
from shipments.models import Agency, Package, Shipment, ShipmentStatus

from .models import ReportExport


class ReportsModuleTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="report_admin", password="Prueba2027!", role=User.Role.ADMIN)
        self.office = User.objects.create_user(username="report_office", password="Prueba2027!", role=User.Role.ADMINISTRATIVE)
        self.operator = User.objects.create_user(username="report_operator", password="Prueba2027!", role=User.Role.OPERATIONAL)
        self.sender = Customer.objects.create(
            customer_type="PERSON", document_type="DNI", document_number="75555555",
            first_name="María", last_name="Torres", phone="955555555", district="Chincha Alta",
            address="Av. Principal 100", created_by=self.admin, updated_by=self.admin,
        )
        self.recipient = Customer.objects.create(
            customer_type="PERSON", document_type="DNI", document_number="76666666",
            first_name="José", last_name="Ramos", phone="966666666", district="La Victoria",
            province="Lima", department="Lima", address="Jr. Destino 200",
            created_by=self.admin, updated_by=self.admin,
        )
        self.origin = Agency.objects.get(code="CHI")
        self.destination = Agency.objects.get(code="LIM")
        self.ready_shipment = self.create_shipment("READY_PICKUP", "PAID")
        delivery = Delivery(
            delivery_method="AGENCY", receiver_type="RECIPIENT",
            receiver_name=self.recipient.display_name, receiver_document_type="DNI",
            receiver_document_number=self.recipient.document_number, receiver_phone=self.recipient.phone,
            verification_method="DOCUMENT_CODE", package_condition="CONFORMING",
        )
        self.delivery = complete_delivery(shipment_id=self.ready_shipment.pk, delivery=delivery, user=self.operator)
        self.transit_shipment = self.create_shipment("IN_TRANSIT", "PENDING")
        incident = Incident(
            agency=self.origin, incident_type="DELAY", severity="HIGH",
            description="Demora operativa registrada para validar los reportes del sistema.",
            public_message="El envío presenta una demora y está siendo revisado.",
        )
        self.incident = report_incident(shipment_id=self.transit_shipment.pk, incident=incident, user=self.operator)

    def create_shipment(self, status_code, payment_status):
        status = ShipmentStatus.objects.get(code=status_code)
        shipment = Shipment.objects.create(
            sender=self.sender, recipient=self.recipient, origin=self.origin, destination=self.destination,
            current_agency=self.destination if status_code == "READY_PICKUP" else self.origin,
            transport_mode="GROUND", service_type="AGENCY", payer="SENDER", payment_timing="ORIGIN",
            payment_status=payment_status, shipping_cost=Decimal("35.00"), current_status=status,
            estimated_delivery_date=timezone.localdate() + timedelta(days=2),
            created_by=self.admin, updated_by=self.operator,
        )
        Package.objects.create(
            shipment=shipment, description="Caja para reporte", quantity=1, weight=Decimal("2.00"),
            length=Decimal("30"), width=Decimal("20"), height=Decimal("15"),
        )
        return shipment

    def filter_query(self):
        today = timezone.localdate()
        return f"date_from={today - timedelta(days=7)}&date_to={today}"

    def test_dashboard_is_available_to_all_internal_roles(self):
        for user in (self.admin, self.office, self.operator):
            self.client.force_login(user)
            response = self.client.get(reverse("dashboard"))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Módulo 6")
            self.assertContains(response, "Envíos registrados")

    def test_module_six_assets_use_cache_busting_version(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "app_v6_1.css?v=6.1.1")
        self.assertContains(response, "dashboard.js?v=6.1.1")

    def test_default_report_dates_render_in_browser_format(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("report_center"))
        today = timezone.localdate().isoformat()
        start = (timezone.localdate() - timedelta(days=29)).isoformat()
        self.assertContains(response, f'value="{start}"')
        self.assertContains(response, f'value="{today}"')

    def test_operational_dashboard_hides_financial_amounts(self):
        self.client.force_login(self.operator)
        response = self.client.get(reverse("dashboard"))
        self.assertNotContains(response, "Ingresos confirmados")
        self.assertContains(response, "Los montos financieros están protegidos")

    def test_administrative_dashboard_can_see_financial_indicator(self):
        self.client.force_login(self.office)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Ingresos confirmados")

    def test_only_administrator_opens_report_center(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("report_center")).status_code, 200)
        self.client.force_login(self.office)
        self.assertEqual(self.client.get(reverse("report_center")).status_code, 403)

    def test_dashboard_rejects_period_longer_than_one_year(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard"), {
            "date_from": timezone.localdate() - timedelta(days=400),
            "date_to": timezone.localdate(),
        })
        self.assertContains(response, "periodo máximo de 366 días")

    def test_csv_export_contains_rows_and_creates_audit(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("report_export", args=["SHIPMENTS", "CSV"]) + "?" + self.filter_query())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn(self.ready_shipment.order_number.encode(), response.content)
        audit = ReportExport.objects.get()
        self.assertEqual(audit.report_type, "SHIPMENTS")
        self.assertEqual(audit.file_format, "CSV")
        self.assertEqual(audit.row_count, 2)

    def test_excel_export_is_valid_xlsx_package(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("report_export", args=["DELIVERIES", "XLSX"]) + "?" + self.filter_query())
        self.assertTrue(response.content.startswith(b"PK"))
        with ZipFile(BytesIO(response.content)) as archive:
            self.assertIn("xl/worksheets/sheet1.xml", archive.namelist())
            self.assertIn(self.ready_shipment.order_number, archive.read("xl/worksheets/sheet1.xml").decode())

    def test_pdf_export_has_pdf_signature(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("report_export", args=["INCIDENTS", "PDF"]) + "?" + self.filter_query())
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF-1.4"))
        self.assertTrue(response.content.endswith(b"%%EOF"))

    def test_non_admin_cannot_export_reports(self):
        self.client.force_login(self.operator)
        response = self.client.get(reverse("report_export", args=["SHIPMENTS", "CSV"]) + "?" + self.filter_query())
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ReportExport.objects.exists())

    def test_export_audit_is_immutable(self):
        audit = ReportExport.objects.create(
            report_type="SHIPMENTS", file_format="CSV", filters={}, row_count=2, requested_by=self.admin,
        )
        audit.row_count = 99
        with self.assertRaises(ValidationError):
            audit.save()
        with self.assertRaises(ValidationError):
            audit.delete()
