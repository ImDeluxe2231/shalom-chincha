from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        ADMINISTRATIVE = "ADMINISTRATIVE", "Administrativo"
        OPERATIONAL = "OPERATIONAL", "Operativo"

    class DocumentType(models.TextChoices):
        DNI = "DNI", "DNI"
        CE = "CE", "Carné de extranjería"

    role = models.CharField(
        "rol", max_length=20, choices=Role.choices, default=Role.OPERATIONAL
    )
    document_type = models.CharField(
        "tipo de documento", max_length=3, choices=DocumentType.choices, default=DocumentType.DNI
    )
    document_number = models.CharField(
        "número de documento", max_length=12, unique=True, blank=True, null=True
    )
    phone = models.CharField("teléfono", max_length=15, blank=True)
    must_change_password = models.BooleanField("debe cambiar contraseña", default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="creado por",
        related_name="created_users",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField("fecha de creación", auto_now_add=True)
    updated_at = models.DateTimeField("última actualización", auto_now=True)

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["first_name", "last_name", "username"]

    @property
    def is_admin_role(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    def __str__(self):
        return f"{self.display_name} ({self.get_role_display()})"
