import secrets
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from customers.models import Customer


class Agency(models.Model):
    code = models.CharField("código", max_length=8, unique=True)
    name = models.CharField("agencia", max_length=120)
    department = models.CharField("departamento", max_length=80)
    province = models.CharField("provincia", max_length=80)
    district = models.CharField("distrito", max_length=80)
    address = models.CharField("dirección", max_length=220, blank=True)
    supports_ground = models.BooleanField("servicio terrestre", default=True)
    supports_air = models.BooleanField("servicio aéreo", default=False)
    is_active = models.BooleanField("activa", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "agencia"
        verbose_name_plural = "agencias"
        ordering = ["department", "province", "name"]

    @property
    def location(self):
        return f"{self.district}, {self.province} - {self.department}"

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} · {self.name} ({self.district})"


class ShipmentStatus(models.Model):
    code = models.CharField("código", max_length=30, unique=True)
    name = models.CharField("estado", max_length=80)
    description = models.CharField("descripción", max_length=220, blank=True)
    color = models.CharField("color", max_length=7, default="#667085")
    sort_order = models.PositiveSmallIntegerField("orden", default=0)
    is_terminal = models.BooleanField("estado final", default=False)

    class Meta:
        verbose_name = "estado de envío"
        verbose_name_plural = "estados de envío"
        ordering = ["sort_order", "name"]

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ShipmentSequence(models.Model):
    year = models.PositiveSmallIntegerField()
    origin = models.ForeignKey(Agency, on_delete=models.PROTECT, related_name="sequences")
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["year", "origin"], name="unique_shipment_sequence")
        ]


class WarehouseLocation(models.Model):
    agency = models.ForeignKey(Agency, on_delete=models.PROTECT, related_name="warehouse_locations", verbose_name="agencia")
    code = models.CharField("código", max_length=20)
    name = models.CharField("ubicación", max_length=100)
    zone = models.CharField("zona", max_length=60, blank=True)
    rack = models.CharField("estante", max_length=30, blank=True)
    level = models.CharField("nivel", max_length=30, blank=True)
    is_active = models.BooleanField("activa", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ubicación de almacén"
        verbose_name_plural = "ubicaciones de almacén"
        ordering = ["agency__code", "code"]
        constraints = [
            models.UniqueConstraint(fields=["agency", "code"], name="unique_location_per_agency")
        ]

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    @property
    def full_label(self):
        details = " · ".join(filter(None, [self.zone, self.rack, self.level]))
        return f"{self.code} - {self.name}" + (f" ({details})" if details else "")

    def __str__(self):
        return f"{self.agency.code} · {self.full_label}"


class Shipment(models.Model):
    class TransportMode(models.TextChoices):
        GROUND = "GROUND", "Terrestre"
        AIR = "AIR", "Aéreo"

    class ServiceType(models.TextChoices):
        AGENCY = "AGENCY", "Agencia a agencia"
        ADDRESS = "ADDRESS", "Entrega a domicilio"

    class Payer(models.TextChoices):
        SENDER = "SENDER", "Remitente"
        RECIPIENT = "RECIPIENT", "Destinatario"

    class PaymentTiming(models.TextChoices):
        ORIGIN = "ORIGIN", "Pago en origen"
        DESTINATION = "DESTINATION", "Pago en destino"

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        PAID = "PAID", "Pagado"

    order_number = models.CharField("número de orden", max_length=24, unique=True, editable=False)
    tracking_code = models.CharField("código de seguimiento", max_length=6, unique=True, editable=False)
    sender = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="shipments_sent", verbose_name="remitente")
    recipient = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="shipments_received", verbose_name="destinatario")
    origin = models.ForeignKey(Agency, on_delete=models.PROTECT, related_name="shipments_origin", verbose_name="agencia de origen")
    destination = models.ForeignKey(Agency, on_delete=models.PROTECT, related_name="shipments_destination", verbose_name="agencia de destino")
    transport_mode = models.CharField("modalidad", max_length=10, choices=TransportMode.choices, default=TransportMode.GROUND)
    service_type = models.CharField("tipo de servicio", max_length=10, choices=ServiceType.choices, default=ServiceType.AGENCY)
    payer = models.CharField("responsable de pago", max_length=10, choices=Payer.choices, default=Payer.SENDER)
    payment_timing = models.CharField("momento de pago", max_length=12, choices=PaymentTiming.choices, default=PaymentTiming.ORIGIN)
    payment_status = models.CharField("estado de pago", max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    shipping_cost = models.DecimalField("costo de envío", max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    insurance_cost = models.DecimalField("seguro", max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(Decimal("0.00"))])
    discount = models.DecimalField("descuento", max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(Decimal("0.00"))])
    estimated_delivery_date = models.DateField("fecha estimada de llegada", blank=True, null=True)
    current_status = models.ForeignKey(ShipmentStatus, on_delete=models.PROTECT, related_name="current_shipments", verbose_name="estado actual")
    current_agency = models.ForeignKey(Agency, on_delete=models.PROTECT, related_name="current_shipments", verbose_name="agencia actual", blank=True, null=True)
    current_location = models.ForeignKey(WarehouseLocation, on_delete=models.PROTECT, related_name="current_shipments", verbose_name="ubicación actual", blank=True, null=True)
    status_changed_at = models.DateTimeField("último cambio de estado", default=timezone.now)
    notes = models.TextField("observaciones", max_length=500, blank=True)
    cancel_reason = models.CharField("motivo de anulación", max_length=300, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_shipments", verbose_name="registrado por")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="updated_shipments", verbose_name="actualizado por")
    created_at = models.DateTimeField("fecha de registro", auto_now_add=True)
    updated_at = models.DateTimeField("última actualización", auto_now=True)

    class Meta:
        verbose_name = "envío"
        verbose_name_plural = "envíos"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order_number"], name="shipment_order_idx"),
            models.Index(fields=["tracking_code"], name="shipment_track_idx"),
            models.Index(fields=["created_at"], name="shipment_date_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.origin_id and self.destination_id and self.origin_id == self.destination_id:
            errors["destination"] = "La agencia de destino debe ser diferente al origen."
        if self.sender_id and not self.sender.is_active:
            errors["sender"] = "El remitente seleccionado está inactivo."
        if self.recipient_id and not self.recipient.is_active:
            errors["recipient"] = "El destinatario seleccionado está inactivo."
        if self.origin_id and self.transport_mode == self.TransportMode.AIR and not self.origin.supports_air:
            errors["transport_mode"] = "La agencia de origen no admite servicio aéreo."
        if self.destination_id and self.transport_mode == self.TransportMode.AIR and not self.destination.supports_air:
            errors["destination"] = "La agencia de destino no admite servicio aéreo."
        if self.origin_id and self.transport_mode == self.TransportMode.GROUND and not self.origin.supports_ground:
            errors["transport_mode"] = "La agencia de origen no admite servicio terrestre."
        if self.destination_id and self.transport_mode == self.TransportMode.GROUND and not self.destination.supports_ground:
            errors["destination"] = "La agencia de destino no admite servicio terrestre."
        if self.discount and self.shipping_cost is not None and self.discount > self.shipping_cost + self.insurance_cost:
            errors["discount"] = "El descuento no puede superar el costo del servicio."
        if self.current_location_id and self.current_agency_id and self.current_location.agency_id != self.current_agency_id:
            errors["current_location"] = "La ubicación debe pertenecer a la agencia actual."
        if errors:
            raise ValidationError(errors)

    def _generate_order_number(self):
        year = timezone.localdate().year
        with transaction.atomic():
            ShipmentSequence.objects.get_or_create(year=year, origin_id=self.origin_id)
            sequence = ShipmentSequence.objects.select_for_update().get(year=year, origin_id=self.origin_id)
            sequence.last_number += 1
            sequence.save(update_fields=["last_number"])
        return f"{self.origin.code}-{year}-{sequence.last_number:06d}"

    @staticmethod
    def _generate_tracking_code():
        for _ in range(30):
            code = f"{secrets.randbelow(1_000_000):06d}"
            if not Shipment.objects.filter(tracking_code=code).exists():
                return code
        raise RuntimeError("No se pudo generar un código de seguimiento único.")

    def save(self, *args, **kwargs):
        validate = kwargs.pop("validate", True)
        if not self.order_number:
            self.order_number = self._generate_order_number()
        if not self.tracking_code:
            self.tracking_code = self._generate_tracking_code()
        if validate:
            self.full_clean()
        super().save(*args, **kwargs)

    @property
    def total_cost(self):
        return (self.shipping_cost or Decimal("0")) + (self.insurance_cost or Decimal("0")) - (self.discount or Decimal("0"))

    @property
    def total_packages(self):
        return sum(package.quantity for package in self.packages.all())

    @property
    def total_actual_weight(self):
        return sum((package.weight * package.quantity for package in self.packages.all()), Decimal("0"))

    @property
    def total_billable_weight(self):
        return sum((package.billable_weight for package in self.packages.all()), Decimal("0"))

    @property
    def can_edit(self):
        return self.current_status.code == "REGISTERED"

    @property
    def next_status_code(self):
        transitions = {
            "REGISTERED": "RECEIVED",
            "RECEIVED": "IN_WAREHOUSE",
            "IN_WAREHOUSE": "DISPATCHED",
            "DISPATCHED": "IN_TRANSIT",
            "IN_TRANSIT": "AT_DESTINATION",
            "AT_DESTINATION": "READY_PICKUP",
        }
        return transitions.get(self.current_status.code)

    @property
    def operational_progress(self):
        progress = {
            "REGISTERED": 8,
            "RECEIVED": 18,
            "IN_WAREHOUSE": 32,
            "DISPATCHED": 48,
            "IN_TRANSIT": 65,
            "AT_DESTINATION": 82,
            "READY_PICKUP": 92,
            "DELIVERED": 100,
            "CANCELED": 100,
            "INCIDENT": 50,
        }
        return progress.get(self.current_status.code, 0)

    @property
    def current_status_label(self):
        if self.current_status.code == "READY_PICKUP" and self.service_type == self.ServiceType.ADDRESS:
            return "Listo para entrega a domicilio"
        return self.current_status.name

    def __str__(self):
        return self.order_number


class Package(models.Model):
    class PackageType(models.TextChoices):
        ENVELOPE = "ENVELOPE", "Sobre"
        PACKAGE = "PACKAGE", "Paquete"
        PARCEL = "PARCEL", "Encomienda"
        CARGO = "CARGO", "Carga"

    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="packages", verbose_name="envío")
    package_type = models.CharField("tipo", max_length=10, choices=PackageType.choices, default=PackageType.PACKAGE)
    description = models.CharField("contenido declarado", max_length=220)
    quantity = models.PositiveSmallIntegerField("bultos", default=1, validators=[MinValueValidator(1)])
    weight = models.DecimalField("peso por bulto (kg)", max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    length = models.DecimalField("largo (cm)", max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    width = models.DecimalField("ancho (cm)", max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    height = models.DecimalField("alto (cm)", max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    declared_value = models.DecimalField("valor declarado", max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(Decimal("0.00"))])
    is_fragile = models.BooleanField("frágil", default=False)
    observations = models.CharField("observaciones", max_length=220, blank=True)

    class Meta:
        verbose_name = "paquete"
        verbose_name_plural = "paquetes"
        ordering = ["id"]

    @property
    def volumetric_weight(self):
        return ((self.length * self.width * self.height) / Decimal("6000")).quantize(Decimal("0.01"))

    @property
    def billable_weight(self):
        return max(self.weight, self.volumetric_weight) * self.quantity

    def __str__(self):
        return f"{self.get_package_type_display()} · {self.description}"


class TrackingEvent(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="tracking_events", verbose_name="envío")
    status = models.ForeignKey(ShipmentStatus, on_delete=models.PROTECT, related_name="events", verbose_name="estado")
    previous_status = models.ForeignKey(ShipmentStatus, on_delete=models.PROTECT, related_name="transitions_from", verbose_name="estado anterior", blank=True, null=True)
    agency = models.ForeignKey(Agency, on_delete=models.PROTECT, related_name="tracking_events", verbose_name="agencia")
    location = models.ForeignKey(WarehouseLocation, on_delete=models.PROTECT, related_name="tracking_events", verbose_name="ubicación de almacén", blank=True, null=True)
    transport_reference = models.CharField("referencia de transporte", max_length=80, blank=True)
    notes = models.CharField("detalle", max_length=300, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="tracking_events", verbose_name="responsable")
    is_system = models.BooleanField("generado por el sistema", default=False)
    visible_to_customer = models.BooleanField("visible para el cliente", default=True)
    created_at = models.DateTimeField("fecha y hora", auto_now_add=True)

    class Meta:
        verbose_name = "evento de seguimiento"
        verbose_name_plural = "eventos de seguimiento"
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.shipment.order_number} · {self.status.name}"

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Los eventos de seguimiento no pueden modificarse.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Los eventos de seguimiento no pueden eliminarse.")
