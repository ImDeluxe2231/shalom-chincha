import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("customers", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Agency",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=8, unique=True, verbose_name="código")),
                ("name", models.CharField(max_length=120, verbose_name="agencia")),
                ("department", models.CharField(max_length=80, verbose_name="departamento")),
                ("province", models.CharField(max_length=80, verbose_name="provincia")),
                ("district", models.CharField(max_length=80, verbose_name="distrito")),
                ("address", models.CharField(blank=True, max_length=220, verbose_name="dirección")),
                ("supports_ground", models.BooleanField(default=True, verbose_name="servicio terrestre")),
                ("supports_air", models.BooleanField(default=False, verbose_name="servicio aéreo")),
                ("is_active", models.BooleanField(default=True, verbose_name="activa")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "agencia", "verbose_name_plural": "agencias", "ordering": ["department", "province", "name"]},
        ),
        migrations.CreateModel(
            name="ShipmentStatus",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=30, unique=True, verbose_name="código")),
                ("name", models.CharField(max_length=80, verbose_name="estado")),
                ("description", models.CharField(blank=True, max_length=220, verbose_name="descripción")),
                ("color", models.CharField(default="#667085", max_length=7, verbose_name="color")),
                ("sort_order", models.PositiveSmallIntegerField(default=0, verbose_name="orden")),
                ("is_terminal", models.BooleanField(default=False, verbose_name="estado final")),
            ],
            options={"verbose_name": "estado de envío", "verbose_name_plural": "estados de envío", "ordering": ["sort_order", "name"]},
        ),
        migrations.CreateModel(
            name="ShipmentSequence",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.PositiveSmallIntegerField()),
                ("last_number", models.PositiveIntegerField(default=0)),
                ("origin", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sequences", to="shipments.agency")),
            ],
        ),
        migrations.CreateModel(
            name="Shipment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order_number", models.CharField(editable=False, max_length=24, unique=True, verbose_name="número de orden")),
                ("tracking_code", models.CharField(editable=False, max_length=6, unique=True, verbose_name="código de seguimiento")),
                ("transport_mode", models.CharField(choices=[("GROUND", "Terrestre"), ("AIR", "Aéreo")], default="GROUND", max_length=10, verbose_name="modalidad")),
                ("service_type", models.CharField(choices=[("AGENCY", "Agencia a agencia"), ("ADDRESS", "Entrega a domicilio")], default="AGENCY", max_length=10, verbose_name="tipo de servicio")),
                ("payer", models.CharField(choices=[("SENDER", "Remitente"), ("RECIPIENT", "Destinatario")], default="SENDER", max_length=10, verbose_name="responsable de pago")),
                ("payment_timing", models.CharField(choices=[("ORIGIN", "Pago en origen"), ("DESTINATION", "Pago en destino")], default="ORIGIN", max_length=12, verbose_name="momento de pago")),
                ("payment_status", models.CharField(choices=[("PENDING", "Pendiente"), ("PAID", "Pagado")], default="PENDING", max_length=10, verbose_name="estado de pago")),
                ("shipping_cost", models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal("0.00"))], verbose_name="costo de envío")),
                ("insurance_cost", models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal("0.00"))], verbose_name="seguro")),
                ("discount", models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal("0.00"))], verbose_name="descuento")),
                ("estimated_delivery_date", models.DateField(blank=True, null=True, verbose_name="fecha estimada de llegada")),
                ("status_changed_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="último cambio de estado")),
                ("notes", models.TextField(blank=True, max_length=500, verbose_name="observaciones")),
                ("cancel_reason", models.CharField(blank=True, max_length=300, verbose_name="motivo de anulación")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="fecha de registro")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="última actualización")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_shipments", to=settings.AUTH_USER_MODEL, verbose_name="registrado por")),
                ("current_status", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="current_shipments", to="shipments.shipmentstatus", verbose_name="estado actual")),
                ("destination", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="shipments_destination", to="shipments.agency", verbose_name="agencia de destino")),
                ("origin", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="shipments_origin", to="shipments.agency", verbose_name="agencia de origen")),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="shipments_received", to="customers.customer", verbose_name="destinatario")),
                ("sender", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="shipments_sent", to="customers.customer", verbose_name="remitente")),
                ("updated_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="updated_shipments", to=settings.AUTH_USER_MODEL, verbose_name="actualizado por")),
            ],
            options={"verbose_name": "envío", "verbose_name_plural": "envíos", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Package",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("package_type", models.CharField(choices=[("ENVELOPE", "Sobre"), ("PACKAGE", "Paquete"), ("PARCEL", "Encomienda"), ("CARGO", "Carga")], default="PACKAGE", max_length=10, verbose_name="tipo")),
                ("description", models.CharField(max_length=220, verbose_name="contenido declarado")),
                ("quantity", models.PositiveSmallIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)], verbose_name="bultos")),
                ("weight", models.DecimalField(decimal_places=2, max_digits=8, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))], verbose_name="peso por bulto (kg)")),
                ("length", models.DecimalField(decimal_places=2, max_digits=8, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))], verbose_name="largo (cm)")),
                ("width", models.DecimalField(decimal_places=2, max_digits=8, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))], verbose_name="ancho (cm)")),
                ("height", models.DecimalField(decimal_places=2, max_digits=8, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))], verbose_name="alto (cm)")),
                ("declared_value", models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal("0.00"))], verbose_name="valor declarado")),
                ("is_fragile", models.BooleanField(default=False, verbose_name="frágil")),
                ("observations", models.CharField(blank=True, max_length=220, verbose_name="observaciones")),
                ("shipment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="packages", to="shipments.shipment", verbose_name="envío")),
            ],
            options={"verbose_name": "paquete", "verbose_name_plural": "paquetes", "ordering": ["id"]},
        ),
        migrations.CreateModel(
            name="TrackingEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("notes", models.CharField(blank=True, max_length=300, verbose_name="detalle")),
                ("is_system", models.BooleanField(default=False, verbose_name="generado por el sistema")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="fecha y hora")),
                ("agency", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="tracking_events", to="shipments.agency", verbose_name="agencia")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="tracking_events", to=settings.AUTH_USER_MODEL, verbose_name="responsable")),
                ("shipment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tracking_events", to="shipments.shipment", verbose_name="envío")),
                ("status", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="events", to="shipments.shipmentstatus", verbose_name="estado")),
            ],
            options={"verbose_name": "evento de seguimiento", "verbose_name_plural": "eventos de seguimiento", "ordering": ["created_at", "id"]},
        ),
        migrations.AddConstraint(model_name="shipmentsequence", constraint=models.UniqueConstraint(fields=("year", "origin"), name="unique_shipment_sequence")),
        migrations.AddIndex(model_name="shipment", index=models.Index(fields=["order_number"], name="shipment_order_idx")),
        migrations.AddIndex(model_name="shipment", index=models.Index(fields=["tracking_code"], name="shipment_track_idx")),
        migrations.AddIndex(model_name="shipment", index=models.Index(fields=["created_at"], name="shipment_date_idx")),
    ]
