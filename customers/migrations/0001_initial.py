import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Customer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("customer_type", models.CharField(choices=[("PERSON", "Persona natural"), ("BUSINESS", "Empresa")], default="PERSON", max_length=12, verbose_name="tipo de cliente")),
                ("document_type", models.CharField(choices=[("DNI", "DNI"), ("CE", "Carné de extranjería"), ("RUC", "RUC")], default="DNI", max_length=3, verbose_name="tipo de documento")),
                ("document_number", models.CharField(max_length=12, unique=True, verbose_name="número de documento")),
                ("first_name", models.CharField(blank=True, max_length=100, verbose_name="nombres")),
                ("last_name", models.CharField(blank=True, max_length=120, verbose_name="apellidos")),
                ("business_name", models.CharField(blank=True, max_length=180, verbose_name="razón social")),
                ("phone", models.CharField(max_length=9, verbose_name="celular")),
                ("secondary_phone", models.CharField(blank=True, max_length=15, verbose_name="teléfono alternativo")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="correo electrónico")),
                ("department", models.CharField(default="Ica", max_length=80, verbose_name="departamento")),
                ("province", models.CharField(default="Chincha", max_length=80, verbose_name="provincia")),
                ("district", models.CharField(max_length=80, verbose_name="distrito")),
                ("address", models.CharField(max_length=220, verbose_name="dirección")),
                ("reference", models.CharField(blank=True, max_length=220, verbose_name="referencia")),
                ("notes", models.TextField(blank=True, max_length=500, verbose_name="observaciones")),
                ("is_active", models.BooleanField(default=True, verbose_name="activo")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="fecha de registro")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="última actualización")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_customers", to=settings.AUTH_USER_MODEL, verbose_name="registrado por")),
                ("updated_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="updated_customers", to=settings.AUTH_USER_MODEL, verbose_name="actualizado por")),
            ],
            options={"verbose_name": "cliente", "verbose_name_plural": "clientes", "ordering": ["last_name", "first_name", "business_name"]},
        ),
        migrations.AddIndex(model_name="customer", index=models.Index(fields=["document_number"], name="customer_doc_idx")),
        migrations.AddIndex(model_name="customer", index=models.Index(fields=["last_name", "first_name"], name="customer_name_idx")),
        migrations.AddIndex(model_name="customer", index=models.Index(fields=["phone"], name="customer_phone_idx")),
    ]
