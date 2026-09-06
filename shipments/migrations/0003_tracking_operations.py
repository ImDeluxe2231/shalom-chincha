import django.db.models.deletion
from django.db import migrations, models


def seed_locations_and_current_agency(apps, schema_editor):
    Agency = apps.get_model("shipments", "Agency")
    Location = apps.get_model("shipments", "WarehouseLocation")
    Shipment = apps.get_model("shipments", "Shipment")
    for agency in Agency.objects.all():
        Location.objects.get_or_create(
            agency=agency,
            code="REC-01",
            defaults={"name": "Zona de recepción", "zone": "Recepción", "rack": "R-01", "level": "Nivel 1", "is_active": True},
        )
        Location.objects.get_or_create(
            agency=agency,
            code="ALM-01",
            defaults={"name": "Almacén general", "zone": "Almacén", "rack": "A-01", "level": "Nivel 1", "is_active": True},
        )
    destination_codes = ["AT_DESTINATION", "READY_PICKUP", "DELIVERED"]
    for shipment in Shipment.objects.select_related("current_status").all():
        shipment.current_agency_id = shipment.destination_id if shipment.current_status.code in destination_codes else shipment.origin_id
        shipment.save(update_fields=["current_agency"])


class Migration(migrations.Migration):
    dependencies = [("shipments", "0002_seed_catalogs")]

    operations = [
        migrations.CreateModel(
            name="WarehouseLocation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=20, verbose_name="código")),
                ("name", models.CharField(max_length=100, verbose_name="ubicación")),
                ("zone", models.CharField(blank=True, max_length=60, verbose_name="zona")),
                ("rack", models.CharField(blank=True, max_length=30, verbose_name="estante")),
                ("level", models.CharField(blank=True, max_length=30, verbose_name="nivel")),
                ("is_active", models.BooleanField(default=True, verbose_name="activa")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("agency", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="warehouse_locations", to="shipments.agency", verbose_name="agencia")),
            ],
            options={"verbose_name": "ubicación de almacén", "verbose_name_plural": "ubicaciones de almacén", "ordering": ["agency__code", "code"]},
        ),
        migrations.AddConstraint(
            model_name="warehouselocation",
            constraint=models.UniqueConstraint(fields=("agency", "code"), name="unique_location_per_agency"),
        ),
        migrations.AddField(
            model_name="shipment",
            name="current_agency",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="current_shipments", to="shipments.agency", verbose_name="agencia actual"),
        ),
        migrations.AddField(
            model_name="shipment",
            name="current_location",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="current_shipments", to="shipments.warehouselocation", verbose_name="ubicación actual"),
        ),
        migrations.AddField(
            model_name="trackingevent",
            name="location",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="tracking_events", to="shipments.warehouselocation", verbose_name="ubicación de almacén"),
        ),
        migrations.AddField(
            model_name="trackingevent",
            name="previous_status",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="transitions_from", to="shipments.shipmentstatus", verbose_name="estado anterior"),
        ),
        migrations.AddField(
            model_name="trackingevent",
            name="transport_reference",
            field=models.CharField(blank=True, max_length=80, verbose_name="referencia de transporte"),
        ),
        migrations.AddField(
            model_name="trackingevent",
            name="visible_to_customer",
            field=models.BooleanField(default=True, verbose_name="visible para el cliente"),
        ),
        migrations.RunPython(seed_locations_and_current_agency, migrations.RunPython.noop),
    ]
