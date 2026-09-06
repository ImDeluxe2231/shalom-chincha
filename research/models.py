from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from shipments.models import Shipment


LIKERT_VALIDATORS = [MinValueValidator(1), MaxValueValidator(5)]


class StudyPhase(models.TextChoices):
    PRETEST = "PRETEST", "Pretest"
    POSTTEST = "POSTTEST", "Postest"


class StudyParticipant(models.Model):
    class Area(models.TextChoices):
        ADMINISTRATIVE = "ADMINISTRATIVE", "Administrativa"
        OPERATIONAL = "OPERATIONAL", "Operativa"

    code = models.CharField("código anónimo", max_length=12, unique=True)
    area = models.CharField("área", max_length=20, choices=Area.choices)
    notes = models.CharField("observaciones", max_length=250, blank=True)
    is_active = models.BooleanField("participante activo", default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="research_participants_created",
        verbose_name="registrado por",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "participante anónimo"
        verbose_name_plural = "participantes anónimos"
        ordering = ["code"]

    def save(self, *args, **kwargs):
        self.code = (self.code or "").strip().upper()
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} · {self.get_area_display()}"


class TraceabilityObservation(models.Model):
    phase = models.CharField("medición", max_length=8, choices=StudyPhase.choices)
    observed_on = models.DateField("fecha de observación", default=timezone.localdate)
    total_registered = models.PositiveIntegerField("total de envíos registrados", validators=[MinValueValidator(1)])
    correctly_tracked = models.PositiveIntegerField("envíos rastreados correctamente")
    notes = models.CharField("observaciones", max_length=300, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="traceability_observations",
        verbose_name="registrado por",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "observación de trazabilidad"
        verbose_name_plural = "observaciones de trazabilidad"
        ordering = ["-observed_on", "-id"]
        indexes = [models.Index(fields=["phase", "observed_on"], name="research_trace_phase_idx")]

    def clean(self):
        super().clean()
        if self.total_registered and self.correctly_tracked > self.total_registered:
            raise ValidationError({"correctly_tracked": "No puede superar el total de envíos registrados."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def percentage(self):
        if not self.total_registered:
            return Decimal("0.00")
        return (Decimal(self.correctly_tracked) * Decimal("100") / Decimal(self.total_registered)).quantize(Decimal("0.01"))

    def __str__(self):
        return f"{self.get_phase_display()} · {self.observed_on} · {self.percentage}%"


class ResponseTimeObservation(models.Model):
    class Operation(models.TextChoices):
        QUERY = "QUERY", "Consulta del estado de un envío"
        UPDATE = "UPDATE", "Actualización del estado de un paquete"

    phase = models.CharField("medición", max_length=8, choices=StudyPhase.choices)
    operation = models.CharField("operación observada", max_length=8, choices=Operation.choices)
    started_at = models.DateTimeField("fecha y hora de inicio")
    finished_at = models.DateTimeField("fecha y hora de finalización")
    duration_seconds = models.DecimalField("duración en segundos", max_digits=12, decimal_places=3, editable=False)
    notes = models.CharField("observaciones", max_length=300, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="response_time_observations",
        verbose_name="registrado por",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "observación de tiempo de respuesta"
        verbose_name_plural = "observaciones de tiempos de respuesta"
        ordering = ["-started_at", "-id"]
        indexes = [models.Index(fields=["phase", "operation"], name="research_time_phase_idx")]

    def clean(self):
        super().clean()
        if self.started_at and self.finished_at and self.finished_at <= self.started_at:
            raise ValidationError({"finished_at": "La finalización debe ser posterior al inicio."})

    def save(self, *args, **kwargs):
        self.full_clean(exclude=["duration_seconds"])
        seconds = Decimal(str((self.finished_at - self.started_at).total_seconds()))
        self.duration_seconds = seconds.quantize(Decimal("0.001"))
        return super().save(*args, **kwargs)

    @property
    def duration_minutes(self):
        return (self.duration_seconds / Decimal("60")).quantize(Decimal("0.01"))

    def __str__(self):
        return f"{self.get_phase_display()} · {self.get_operation_display()} · {self.duration_minutes} min"


class EfficiencySurvey(models.Model):
    participant = models.ForeignKey(
        StudyParticipant,
        on_delete=models.PROTECT,
        related_name="surveys",
        verbose_name="participante",
    )
    phase = models.CharField("medición", max_length=8, choices=StudyPhase.choices)
    observed_on = models.DateField("fecha de aplicación", default=timezone.localdate)
    q1 = models.PositiveSmallIntegerField("P1 · Rapidez de atención", validators=LIKERT_VALIDATORS)
    q2 = models.PositiveSmallIntegerField("P2 · Exactitud de ubicación", validators=LIKERT_VALIDATORS)
    q3 = models.PositiveSmallIntegerField("P3 · Resolución de problemas", validators=LIKERT_VALIDATORS)
    q4 = models.PositiveSmallIntegerField("P4 · Tiempo de registro", validators=LIKERT_VALIDATORS)
    q5 = models.PositiveSmallIntegerField("P5 · Atención en ventanilla", validators=LIKERT_VALIDATORS)
    q6 = models.PositiveSmallIntegerField("P6 · Organización del personal", validators=LIKERT_VALIDATORS)
    q7 = models.PositiveSmallIntegerField("P7 · Condición de encomiendas", validators=LIKERT_VALIDATORS)
    q8 = models.PositiveSmallIntegerField("P8 · Organización del almacén", validators=LIKERT_VALIDATORS)
    q9 = models.PositiveSmallIntegerField("P9 · Exactitud sistema/almacén", validators=LIKERT_VALIDATORS)
    q10 = models.PositiveSmallIntegerField("P10 · Eficiencia general", validators=LIKERT_VALIDATORS)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="efficiency_surveys_recorded",
        verbose_name="registrado por",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "cuestionario de eficiencia"
        verbose_name_plural = "cuestionarios de eficiencia"
        ordering = ["phase", "participant__code"]
        constraints = [
            models.UniqueConstraint(fields=["participant", "phase"], name="research_unique_survey_phase")
        ]
        indexes = [models.Index(fields=["phase", "observed_on"], name="research_survey_phase_idx")]

    @property
    def answers(self):
        return [getattr(self, f"q{number}") for number in range(1, 11)]

    @property
    def total_score(self):
        return sum(self.answers)

    @property
    def average_score(self):
        return Decimal(str(self.total_score / 10)).quantize(Decimal("0.01"))

    @property
    def administrative_average(self):
        return Decimal(str(sum(self.answers[:5]) / 5)).quantize(Decimal("0.01"))

    @property
    def operational_average(self):
        return Decimal(str(sum(self.answers[5:]) / 5)).quantize(Decimal("0.01"))

    def __str__(self):
        return f"{self.participant.code} · {self.get_phase_display()} · {self.average_score}/5"


class OperationMetric(models.Model):
    class Operation(models.TextChoices):
        QUERY = "QUERY", "Consulta de seguimiento"
        UPDATE = "UPDATE", "Actualización de estado"

    class Source(models.TextChoices):
        PUBLIC = "PUBLIC", "Consulta pública"
        INTERNAL = "INTERNAL", "Consulta interna"
        STATUS = "STATUS", "Flujo de estados"

    operation = models.CharField("operación", max_length=8, choices=Operation.choices)
    source = models.CharField("origen", max_length=10, choices=Source.choices)
    success = models.BooleanField("operación exitosa")
    duration_ms = models.PositiveIntegerField("duración en milisegundos")
    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.SET_NULL,
        related_name="operation_metrics",
        null=True,
        blank=True,
        verbose_name="envío",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="operation_metrics",
        null=True,
        blank=True,
        verbose_name="usuario",
    )
    details = models.JSONField("detalle técnico", default=dict, blank=True)
    created_at = models.DateTimeField("fecha y hora", auto_now_add=True)

    class Meta:
        verbose_name = "métrica automática"
        verbose_name_plural = "métricas automáticas"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["operation", "created_at"], name="research_metric_op_idx"),
            models.Index(fields=["success", "created_at"], name="research_metric_ok_idx"),
        ]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Las métricas automáticas son inalterables.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Las métricas automáticas no pueden eliminarse.")


class CustomerNotification(models.Model):
    class Event(models.TextChoices):
        STATUS = "STATUS", "Cambio de estado"
        INCIDENT = "INCIDENT", "Incidencia reportada"
        RESOLVED = "RESOLVED", "Incidencia resuelta"
        DELIVERY = "DELIVERY", "Entrega confirmada"

    class Status(models.TextChoices):
        SENT = "SENT", "Enviada"
        SKIPPED = "SKIPPED", "Omitida"
        FAILED = "FAILED", "Fallida"

    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.PROTECT,
        related_name="customer_notifications",
        verbose_name="envío",
    )
    event = models.CharField("evento", max_length=10, choices=Event.choices)
    recipient_email = models.EmailField("correo de destino", blank=True)
    subject = models.CharField("asunto", max_length=180)
    message = models.TextField("mensaje", max_length=1200)
    status = models.CharField("resultado", max_length=8, choices=Status.choices)
    error_message = models.CharField("detalle del resultado", max_length=300, blank=True)
    created_at = models.DateTimeField("fecha y hora", auto_now_add=True)

    class Meta:
        verbose_name = "notificación automática"
        verbose_name_plural = "notificaciones automáticas"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"], name="research_notice_status_idx")]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("La bitácora de notificaciones es inalterable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("La bitácora de notificaciones no puede eliminarse.")

