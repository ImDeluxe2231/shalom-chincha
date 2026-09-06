import django.core.validators
import django.db.models.deletion
import django.utils.timezone
import operations.models
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("shipments", "0003_tracking_operations"),
    ]

    operations = [
        migrations.CreateModel(
            name="Delivery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("delivery_method", models.CharField(choices=[("AGENCY", "Recojo en agencia"), ("ADDRESS", "Entrega a domicilio")], max_length=12, verbose_name="modalidad de entrega")),
                ("receiver_type", models.CharField(choices=[("RECIPIENT", "Destinatario"), ("AUTHORIZED", "Persona autorizada")], max_length=12, verbose_name="persona que recibe")),
                ("receiver_name", models.CharField(max_length=180, verbose_name="nombre completo del receptor")),
                ("receiver_document_type", models.CharField(choices=[("DNI", "DNI"), ("CE", "Carné de extranjería")], max_length=3, verbose_name="tipo de documento")),
                ("receiver_document_number", models.CharField(max_length=12, verbose_name="número de documento")),
                ("receiver_phone", models.CharField(blank=True, max_length=9, verbose_name="celular del receptor")),
                ("relationship", models.CharField(blank=True, max_length=80, verbose_name="relación con el destinatario")),
                ("verification_method", models.CharField(choices=[("DOCUMENT_CODE", "Documento y código de seguimiento"), ("AUTHORIZATION", "Documento, código y autorización")], max_length=20, verbose_name="método de verificación")),
                ("package_condition", models.CharField(choices=[("CONFORMING", "Conforme"), ("OBSERVED", "Entregado con observaciones")], default="CONFORMING", max_length=12, verbose_name="condición de los bultos")),
                ("condition_notes", models.CharField(blank=True, max_length=300, verbose_name="observaciones de entrega")),
                ("packages_delivered", models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1)], verbose_name="bultos entregados")),
                ("payment_confirmed", models.BooleanField(default=False, verbose_name="pago confirmado")),
                ("notes", models.CharField(blank=True, max_length=300, verbose_name="nota interna")),
                ("verification_code", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="código de verificación")),
                ("delivered_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="fecha y hora de entrega")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("agency", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="deliveries", to="shipments.agency", verbose_name="agencia de entrega")),
                ("delivered_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="deliveries_completed", to=settings.AUTH_USER_MODEL, verbose_name="entregado por")),
                ("shipment", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="delivery", to="shipments.shipment", verbose_name="envío")),
            ],
            options={"verbose_name": "entrega", "verbose_name_plural": "entregas", "ordering": ["-delivered_at"]},
        ),
        migrations.CreateModel(
            name="Incident",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(editable=False, max_length=20, unique=True, verbose_name="código")),
                ("incident_type", models.CharField(choices=[("DELAY", "Demora"), ("DAMAGE", "Daño del paquete"), ("LOSS", "Pérdida o faltante"), ("ADDRESS", "Problema de dirección"), ("DOCUMENT", "Problema de documentación"), ("PAYMENT", "Problema de pago"), ("OPERATIONAL", "Error operativo"), ("OTHER", "Otro")], max_length=15, verbose_name="tipo")),
                ("severity", models.CharField(choices=[("LOW", "Baja"), ("MEDIUM", "Media"), ("HIGH", "Alta"), ("CRITICAL", "Crítica")], default="MEDIUM", max_length=10, verbose_name="gravedad")),
                ("status", models.CharField(choices=[("OPEN", "Abierta"), ("IN_REVIEW", "En revisión"), ("RESOLVED", "Resuelta")], default="OPEN", max_length=10, verbose_name="situación")),
                ("description", models.TextField(max_length=1000, verbose_name="descripción interna")),
                ("public_message", models.CharField(blank=True, max_length=300, verbose_name="mensaje para el cliente")),
                ("evidence", models.FileField(blank=True, upload_to=operations.models.incident_evidence_path, validators=[django.core.validators.FileExtensionValidator(["jpg", "jpeg", "png", "pdf"]), operations.models.validate_evidence_size], verbose_name="evidencia")),
                ("resolution", models.TextField(blank=True, max_length=1000, verbose_name="resolución")),
                ("reported_at", models.DateTimeField(auto_now_add=True, verbose_name="fecha de reporte")),
                ("resolved_at", models.DateTimeField(blank=True, null=True, verbose_name="fecha de resolución")),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("agency", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="incidents", to="shipments.agency", verbose_name="agencia")),
                ("assigned_to", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="assigned_incidents", to=settings.AUTH_USER_MODEL, verbose_name="asignado a")),
                ("previous_status", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="incidents_interrupted", to="shipments.shipmentstatus", verbose_name="estado previo")),
                ("reported_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reported_incidents", to=settings.AUTH_USER_MODEL, verbose_name="reportado por")),
                ("resolved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="resolved_incidents", to=settings.AUTH_USER_MODEL, verbose_name="resuelto por")),
                ("shipment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="incidents", to="shipments.shipment", verbose_name="envío")),
            ],
            options={"verbose_name": "incidencia", "verbose_name_plural": "incidencias", "ordering": ["-reported_at"]},
        ),
        migrations.CreateModel(
            name="IncidentAction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("REPORTED", "Incidencia reportada"), ("ASSIGNED", "Asignada para revisión"), ("RESOLVED", "Incidencia resuelta")], max_length=10, verbose_name="acción")),
                ("notes", models.CharField(max_length=500, verbose_name="detalle")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="fecha y hora")),
                ("incident", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="actions", to="operations.incident", verbose_name="incidencia")),
                ("performed_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="incident_actions", to=settings.AUTH_USER_MODEL, verbose_name="realizado por")),
            ],
            options={"verbose_name": "acción de incidencia", "verbose_name_plural": "acciones de incidencia", "ordering": ["created_at", "id"]},
        ),
        migrations.AddIndex(model_name="delivery", index=models.Index(fields=["delivered_at"], name="delivery_date_idx")),
        migrations.AddIndex(model_name="incident", index=models.Index(fields=["status", "severity"], name="incident_status_idx")),
        migrations.AddIndex(model_name="incident", index=models.Index(fields=["reported_at"], name="incident_date_idx")),
    ]
