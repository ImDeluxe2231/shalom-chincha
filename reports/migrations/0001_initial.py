import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="ReportExport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("report_type", models.CharField(choices=[("SHIPMENTS", "Envíos"), ("DELIVERIES", "Entregas"), ("INCIDENTS", "Incidencias")], max_length=12, verbose_name="reporte")),
                ("file_format", models.CharField(choices=[("CSV", "CSV"), ("XLSX", "Excel"), ("PDF", "PDF")], max_length=5, verbose_name="formato")),
                ("filters", models.JSONField(blank=True, default=dict, verbose_name="filtros aplicados")),
                ("row_count", models.PositiveIntegerField(verbose_name="filas exportadas")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="fecha y hora")),
                ("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="report_exports", to=settings.AUTH_USER_MODEL, verbose_name="solicitado por")),
            ],
            options={"verbose_name": "exportación de reporte", "verbose_name_plural": "exportaciones de reportes", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="reportexport", index=models.Index(fields=["report_type", "created_at"], name="report_type_date_idx")),
    ]
