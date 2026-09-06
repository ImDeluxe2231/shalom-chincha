import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Customer(models.Model):
    class CustomerType(models.TextChoices):
        PERSON = "PERSON", "Persona natural"
        BUSINESS = "BUSINESS", "Empresa"

    class DocumentType(models.TextChoices):
        DNI = "DNI", "DNI"
        CE = "CE", "Carné de extranjería"
        RUC = "RUC", "RUC"

    customer_type = models.CharField(
        "tipo de cliente", max_length=12, choices=CustomerType.choices, default=CustomerType.PERSON
    )
    document_type = models.CharField(
        "tipo de documento", max_length=3, choices=DocumentType.choices, default=DocumentType.DNI
    )
    document_number = models.CharField("número de documento", max_length=12, unique=True)
    first_name = models.CharField("nombres", max_length=100, blank=True)
    last_name = models.CharField("apellidos", max_length=120, blank=True)
    business_name = models.CharField("razón social", max_length=180, blank=True)
    phone = models.CharField("celular", max_length=9)
    secondary_phone = models.CharField("teléfono alternativo", max_length=15, blank=True)
    email = models.EmailField("correo electrónico", blank=True)
    department = models.CharField("departamento", max_length=80, default="Ica")
    province = models.CharField("provincia", max_length=80, default="Chincha")
    district = models.CharField("distrito", max_length=80)
    address = models.CharField("dirección", max_length=220)
    reference = models.CharField("referencia", max_length=220, blank=True)
    notes = models.TextField("observaciones", blank=True, max_length=500)
    is_active = models.BooleanField("activo", default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="registrado por",
        related_name="created_customers",
        on_delete=models.PROTECT,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="actualizado por",
        related_name="updated_customers",
        on_delete=models.PROTECT,
    )
    created_at = models.DateTimeField("fecha de registro", auto_now_add=True)
    updated_at = models.DateTimeField("última actualización", auto_now=True)

    class Meta:
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        ordering = ["last_name", "first_name", "business_name"]
        indexes = [
            models.Index(fields=["document_number"], name="customer_doc_idx"),
            models.Index(fields=["last_name", "first_name"], name="customer_name_idx"),
            models.Index(fields=["phone"], name="customer_phone_idx"),
        ]

    def clean(self):
        super().clean()
        self.document_number = (self.document_number or "").strip().upper()
        self.phone = re.sub(r"\D", "", self.phone or "")
        self.first_name = (self.first_name or "").strip()
        self.last_name = (self.last_name or "").strip()
        self.business_name = (self.business_name or "").strip()

        errors = {}
        if self.customer_type == self.CustomerType.PERSON:
            if not self.first_name:
                errors["first_name"] = "Ingresa los nombres de la persona."
            if not self.last_name:
                errors["last_name"] = "Ingresa los apellidos de la persona."
            if self.document_type == self.DocumentType.RUC:
                errors["document_type"] = "Una persona natural debe registrarse con DNI o CE."
        else:
            if not self.business_name:
                errors["business_name"] = "Ingresa la razón social de la empresa."
            if self.document_type != self.DocumentType.RUC:
                errors["document_type"] = "Una empresa debe registrarse con RUC."

        if self.document_type == self.DocumentType.DNI and not re.fullmatch(r"\d{8}", self.document_number):
            errors["document_number"] = "El DNI debe contener exactamente 8 dígitos."
        elif self.document_type == self.DocumentType.RUC and not re.fullmatch(r"\d{11}", self.document_number):
            errors["document_number"] = "El RUC debe contener exactamente 11 dígitos."
        elif self.document_type == self.DocumentType.CE and not re.fullmatch(r"[A-Z0-9]{9,12}", self.document_number):
            errors["document_number"] = "El carné debe contener entre 9 y 12 caracteres."

        if not re.fullmatch(r"9\d{8}", self.phone):
            errors["phone"] = "Ingresa un celular peruano válido de 9 dígitos."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def display_name(self):
        if self.customer_type == self.CustomerType.BUSINESS:
            return self.business_name
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def location(self):
        return ", ".join(filter(None, [self.district, self.province, self.department]))

    def __str__(self):
        return f"{self.display_name} - {self.document_type} {self.document_number}"
