from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ReportExport(models.Model):
    class ReportType(models.TextChoices):
        SHIPMENTS = "SHIPMENTS", "Envíos"
        DELIVERIES = "DELIVERIES", "Entregas"
        INCIDENTS = "INCIDENTS", "Incidencias"

    class FileFormat(models.TextChoices):
        CSV = "CSV", "CSV"
        XLSX = "XLSX", "Excel"
        PDF = "PDF", "PDF"

    report_type = models.CharField("reporte", max_length=12, choices=ReportType.choices)
    file_format = models.CharField("formato", max_length=5, choices=FileFormat.choices)
    filters = models.JSONField("filtros aplicados", default=dict, blank=True)
    row_count = models.PositiveIntegerField("filas exportadas")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="report_exports",
        verbose_name="solicitado por",
    )
    created_at = models.DateTimeField("fecha y hora", auto_now_add=True)

    class Meta:
        verbose_name = "exportación de reporte"
        verbose_name_plural = "exportaciones de reportes"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["report_type", "created_at"], name="report_type_date_idx")]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("La bitácora de exportaciones no puede modificarse.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("La bitácora de exportaciones no puede eliminarse.")

    def __str__(self):
        return f"{self.get_report_type_display()} · {self.file_format} · {self.created_at:%d/%m/%Y %H:%M}"
