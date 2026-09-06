import re
import secrets
import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from shipments.models import Agency, Shipment, ShipmentStatus


def validate_evidence_size(file):
    if file.size > 5 * 1024 * 1024:
        raise ValidationError("La evidencia no puede superar los 5 MB.")
    content_type = getattr(file, "content_type", None)
    allowed_types = {"image/jpeg", "image/png", "application/pdf"}
    if content_type and content_type not in allowed_types:
        raise ValidationError("El contenido del archivo no corresponde a JPG, PNG o PDF.")


def incident_evidence_path(instance, filename):
    extension = Path(filename).suffix.lower()
    return f"incidents/{timezone.localdate().year}/{uuid.uuid4().hex}{extension}"


class Delivery(models.Model):
    class DeliveryMethod(models.TextChoices):
        AGENCY = "AGENCY", "Recojo en agencia"
        ADDRESS = "ADDRESS", "Entrega a domicilio"

    class ReceiverType(models.TextChoices):
        RECIPIENT = "RECIPIENT", "Destinatario"
        AUTHORIZED = "AUTHORIZED", "Persona autorizada"

    class DocumentType(models.TextChoices):
        DNI = "DNI", "DNI"
        CE = "CE", "Carné de extranjería"

    class VerificationMethod(models.TextChoices):
        DOCUMENT_CODE = "DOCUMENT_CODE", "Documento y código de seguimiento"
        AUTHORIZATION = "AUTHORIZATION", "Documento, código y autorización"

    class PackageCondition(models.TextChoices):
        CONFORMING = "CONFORMING", "Conforme"
        OBSERVED = "OBSERVED", "Entregado con observaciones"

    shipment = models.OneToOneField(Shipment, on_delete=models.PROTECT, related_name="delivery", verbose_name="envío")
    agency = models.ForeignKey(Agency, on_delete=models.PROTECT, related_name="deliveries", verbose_name="agencia de entrega")
    delivery_method = models.CharField("modalidad de entrega", max_length=12, choices=DeliveryMethod.choices)
    receiver_type = models.CharField("persona que recibe", max_length=12, choices=ReceiverType.choices)
    receiver_name = models.CharField("nombre completo del receptor", max_length=180)
    receiver_document_type = models.CharField("tipo de documento", max_length=3, choices=DocumentType.choices)
    receiver_document_number = models.CharField("número de documento", max_length=12)
    receiver_phone = models.CharField("celular del receptor", max_length=9, blank=True)
    relationship = models.CharField("relación con el destinatario", max_length=80, blank=True)
    verification_method = models.CharField("método de verificación", max_length=20, choices=VerificationMethod.choices)
    package_condition = models.CharField("condición de los bultos", max_length=12, choices=PackageCondition.choices, default=PackageCondition.CONFORMING)
    condition_notes = models.CharField("observaciones de entrega", max_length=300, blank=True)
    packages_delivered = models.PositiveSmallIntegerField("bultos entregados", validators=[MinValueValidator(1)])
    payment_confirmed = models.BooleanField("pago confirmado", default=False)
    notes = models.CharField("nota interna", max_length=300, blank=True)
    verification_code = models.UUIDField("código de verificación", default=uuid.uuid4, unique=True, editable=False)
    delivered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="deliveries_completed", verbose_name="entregado por")
    delivered_at = models.DateTimeField("fecha y hora de entrega", default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "entrega"
        verbose_name_plural = "entregas"
        ordering = ["-delivered_at"]
        indexes = [models.Index(fields=["delivered_at"], name="delivery_date_idx")]

    def clean(self):
        super().clean()
        errors = {}
        document = (self.receiver_document_number or "").strip().upper()
        phone = re.sub(r"\D", "", self.receiver_phone or "")
        self.receiver_document_number = document
        self.receiver_phone = phone
        self.receiver_name = (self.receiver_name or "").strip()
        if self.receiver_document_type == self.DocumentType.DNI and not re.fullmatch(r"\d{8}", document):
            errors["receiver_document_number"] = "El DNI debe contener exactamente 8 dígitos."
        if self.receiver_document_type == self.DocumentType.CE and not re.fullmatch(r"[A-Z0-9]{9,12}", document):
            errors["receiver_document_number"] = "El carné debe contener entre 9 y 12 caracteres."
        if phone and not re.fullmatch(r"9\d{8}", phone):
            errors["receiver_phone"] = "Ingresa un celular peruano válido de 9 dígitos."
        if self.receiver_type == self.ReceiverType.AUTHORIZED and not self.relationship.strip():
            errors["relationship"] = "Indica la relación de la persona autorizada con el destinatario."
        if self.package_condition == self.PackageCondition.OBSERVED and not self.condition_notes.strip():
            errors["condition_notes"] = "Describe las observaciones de los bultos entregados."
        if self.shipment_id and self.packages_delivered != self.shipment.total_packages:
            errors["packages_delivered"] = "La cantidad entregada debe coincidir con los bultos registrados."
        if self.shipment_id and self.agency_id != self.shipment.destination_id:
            errors["agency"] = "La entrega debe registrarse en la agencia de destino."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("La constancia de entrega no puede modificarse.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("La constancia de entrega no puede eliminarse.")

    @property
    def masked_document(self):
        value = self.receiver_document_number
        return f"{'*' * max(0, len(value) - 4)}{value[-4:]}"

    @property
    def masked_receiver_name(self):
        return " ".join(f"{part[0]}***" for part in self.receiver_name.split() if part)

    def __str__(self):
        return f"Entrega {self.shipment.order_number}"


class Incident(models.Model):
    class IncidentType(models.TextChoices):
        DELAY = "DELAY", "Demora"
        DAMAGE = "DAMAGE", "Daño del paquete"
        LOSS = "LOSS", "Pérdida o faltante"
        ADDRESS = "ADDRESS", "Problema de dirección"
        DOCUMENT = "DOCUMENT", "Problema de documentación"
        PAYMENT = "PAYMENT", "Problema de pago"
        OPERATIONAL = "OPERATIONAL", "Error operativo"
        OTHER = "OTHER", "Otro"

    class Severity(models.TextChoices):
        LOW = "LOW", "Baja"
        MEDIUM = "MEDIUM", "Media"
        HIGH = "HIGH", "Alta"
        CRITICAL = "CRITICAL", "Crítica"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Abierta"
        IN_REVIEW = "IN_REVIEW", "En revisión"
        RESOLVED = "RESOLVED", "Resuelta"

    code = models.CharField("código", max_length=20, unique=True, editable=False)
    shipment = models.ForeignKey(Shipment, on_delete=models.PROTECT, related_name="incidents", verbose_name="envío")
    previous_status = models.ForeignKey(ShipmentStatus, on_delete=models.PROTECT, related_name="incidents_interrupted", verbose_name="estado previo")
    agency = models.ForeignKey(Agency, on_delete=models.PROTECT, related_name="incidents", verbose_name="agencia")
    incident_type = models.CharField("tipo", max_length=15, choices=IncidentType.choices)
    severity = models.CharField("gravedad", max_length=10, choices=Severity.choices, default=Severity.MEDIUM)
    status = models.CharField("situación", max_length=10, choices=Status.choices, default=Status.OPEN)
    description = models.TextField("descripción interna", max_length=1000)
    public_message = models.CharField("mensaje para el cliente", max_length=300, blank=True)
    evidence = models.FileField(
        "evidencia",
        upload_to=incident_evidence_path,
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "pdf"]), validate_evidence_size],
    )
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assigned_incidents", verbose_name="asignado a", blank=True, null=True)
    resolution = models.TextField("resolución", max_length=1000, blank=True)
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reported_incidents", verbose_name="reportado por")
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="resolved_incidents", verbose_name="resuelto por", blank=True, null=True)
    reported_at = models.DateTimeField("fecha de reporte", auto_now_add=True)
    resolved_at = models.DateTimeField("fecha de resolución", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "incidencia"
        verbose_name_plural = "incidencias"
        ordering = ["-reported_at"]
        indexes = [
            models.Index(fields=["status", "severity"], name="incident_status_idx"),
            models.Index(fields=["reported_at"], name="incident_date_idx"),
        ]

    def _generate_code(self):
        year = timezone.localdate().year
        for _ in range(30):
            code = f"INC-{year}-{secrets.token_hex(3).upper()}"
            if not type(self).objects.filter(code=code).exists():
                return code
        raise RuntimeError("No se pudo generar el código de incidencia.")

    @property
    def is_active(self):
        return self.status != self.Status.RESOLVED

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self._generate_code()
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} · {self.shipment.order_number}"


class IncidentAction(models.Model):
    class Action(models.TextChoices):
        REPORTED = "REPORTED", "Incidencia reportada"
        ASSIGNED = "ASSIGNED", "Asignada para revisión"
        RESOLVED = "RESOLVED", "Incidencia resuelta"

    incident = models.ForeignKey(Incident, on_delete=models.PROTECT, related_name="actions", verbose_name="incidencia")
    action = models.CharField("acción", max_length=10, choices=Action.choices)
    notes = models.CharField("detalle", max_length=500)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="incident_actions", verbose_name="realizado por")
    created_at = models.DateTimeField("fecha y hora", auto_now_add=True)

    class Meta:
        verbose_name = "acción de incidencia"
        verbose_name_plural = "acciones de incidencia"
        ordering = ["created_at", "id"]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("El historial de la incidencia no puede modificarse.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("El historial de la incidencia no puede eliminarse.")

    def __str__(self):
        return f"{self.incident.code} · {self.get_action_display()}"
