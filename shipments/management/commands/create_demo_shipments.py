from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from customers.models import Customer
from shipments.models import Agency, Package, Shipment, ShipmentStatus, TrackingEvent


class Command(BaseCommand):
    help = "Crea un envío demostrativo completo para el módulo 3"

    def handle(self, *args, **options):
        user = User.objects.filter(username="admin").first()
        customers = list(Customer.objects.filter(is_active=True)[:2])
        origin = Agency.objects.filter(code="CHI").first()
        destination = Agency.objects.filter(code="LIM").first()
        status = ShipmentStatus.objects.filter(code="REGISTERED").first()
        if not user or len(customers) < 2:
            raise CommandError("Ejecuta primero create_demo_users y create_demo_customers.")
        if not all([origin, destination, status]):
            raise CommandError("Ejecuta primero python manage.py migrate.")
        if Shipment.objects.filter(notes__contains="ENVÍO DEMOSTRATIVO").exists():
            self.stdout.write(self.style.WARNING("El envío demostrativo ya existe."))
            return
        with transaction.atomic():
            shipment = Shipment.objects.create(
                sender=customers[0], recipient=customers[1], origin=origin, destination=destination,
                transport_mode="GROUND", service_type="AGENCY", payer="SENDER", payment_timing="ORIGIN",
                payment_status="PAID", shipping_cost=Decimal("25.00"), insurance_cost=Decimal("2.50"),
                discount=Decimal("0.00"), current_status=status, notes="ENVÍO DEMOSTRATIVO DEL MÓDULO 3",
                current_agency=origin,
                created_by=user, updated_by=user,
            )
            Package.objects.create(
                shipment=shipment, package_type="PACKAGE", description="Prendas de vestir",
                quantity=1, weight=Decimal("2.50"), length=Decimal("35"), width=Decimal("25"),
                height=Decimal("20"), declared_value=Decimal("120.00"), is_fragile=False,
            )
            TrackingEvent.objects.create(
                shipment=shipment, status=status, agency=origin,
                notes="Envío registrado y recibido en ventanilla.", created_by=user, is_system=True,
            )
        self.stdout.write(self.style.SUCCESS(f"Creado: {shipment.order_number} / {shipment.tracking_code}"))
