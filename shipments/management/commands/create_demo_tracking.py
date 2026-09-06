from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from shipments.models import Shipment, WarehouseLocation
from shipments.tracking_services import register_transition


class Command(BaseCommand):
    help = "Avanza el envío demostrativo hasta almacén de origen"

    def handle(self, *args, **options):
        shipment = Shipment.objects.filter(notes__contains="ENVÍO DEMOSTRATIVO").select_related("current_status", "origin").first()
        user = User.objects.filter(username="almacen").first() or User.objects.filter(username="admin").first()
        if not shipment or not user:
            raise CommandError("Ejecuta primero create_demo_users, create_demo_customers y create_demo_shipments.")
        if shipment.current_status.code == "REGISTERED":
            register_transition(shipment_id=shipment.pk, target_code="RECEIVED", user=user, notes="Bultos verificados sin observaciones.")
            shipment.refresh_from_db()
        if shipment.current_status.code == "RECEIVED":
            location = WarehouseLocation.objects.filter(agency=shipment.origin, code="ALM-01").first()
            if location is None:
                raise CommandError("No existe la ubicación ALM-01 de la agencia de origen. Ejecuta migrate.")
            register_transition(shipment_id=shipment.pk, target_code="IN_WAREHOUSE", user=user, location=location, notes="Envío ubicado en almacén de origen.")
            shipment.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(f"{shipment.order_number}: {shipment.current_status.name}"))
