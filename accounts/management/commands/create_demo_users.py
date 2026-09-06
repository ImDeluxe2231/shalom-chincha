import secrets

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User


class Command(BaseCommand):
    help = "Crea usuarios locales de demostración con contraseñas aleatorias."

    USERS = (
        {"username": "admin", "first_name": "Administrador", "last_name": "Demo", "email": "admin@shalom-chincha.test", "role": User.Role.ADMIN, "is_staff": True, "is_superuser": True},
        {"username": "ventanilla", "first_name": "Personal", "last_name": "Administrativo", "email": "ventanilla@shalom-chincha.test", "role": User.Role.ADMINISTRATIVE},
        {"username": "almacen", "first_name": "Personal", "last_name": "Operativo", "email": "almacen@shalom-chincha.test", "role": User.Role.OPERATIONAL},
    )

    def handle(self, *args, **options):
        if not settings.DEBUG or getattr(settings, "PRODUCTION", False):
            raise CommandError("Este comando solo está disponible en desarrollo local.")
        for data in self.USERS:
            user, created = User.objects.get_or_create(username=data["username"], defaults=data)
            if created:
                password = secrets.token_urlsafe(24)
                user.set_password(password)
                user.save(update_fields=["password"])
                self.stdout.write(self.style.SUCCESS(f"Creado: {user.username} | Contraseña: {password}"))
            else:
                self.stdout.write(f"Ya existe: {user.username}. No se modificó su contraseña.")
        self.stdout.write("Guarda las contraseñas en un lugar privado. No las publiques ni compartas capturas de la consola.")
