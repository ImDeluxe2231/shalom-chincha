from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from customers.models import Customer


class Command(BaseCommand):
    help = "Crea clientes demostrativos para el módulo 2"

    def handle(self, *args, **options):
        user = User.objects.filter(username="admin").first() or User.objects.filter(is_superuser=True).first()
        if not user:
            raise CommandError("Primero ejecuta: python manage.py create_demo_users")

        records = [
            {
                "customer_type": "PERSON", "document_type": "DNI", "document_number": "71234567",
                "first_name": "Andrea", "last_name": "Mendoza Rojas", "phone": "987654321",
                "email": "andrea@example.com", "department": "Ica", "province": "Chincha",
                "district": "Chincha Alta", "address": "Av. Benavides 245", "reference": "Cerca de la plaza",
            },
            {
                "customer_type": "PERSON", "document_type": "DNI", "document_number": "72345678",
                "first_name": "Carlos", "last_name": "Quispe Huamán", "phone": "976543210",
                "email": "carlos@example.com", "department": "Ica", "province": "Chincha",
                "district": "Pueblo Nuevo", "address": "Calle Los Olivos 108", "reference": "Frente al mercado",
            },
            {
                "customer_type": "BUSINESS", "document_type": "RUC", "document_number": "20601234567",
                "business_name": "Comercial Chincha S.A.C.", "phone": "965432109",
                "email": "pedidos@comercialchincha.test", "department": "Ica", "province": "Chincha",
                "district": "Grocio Prado", "address": "Panamericana Sur km 196", "reference": "Almacén principal",
            },
        ]
        for record in records:
            _, created = Customer.objects.get_or_create(
                document_number=record["document_number"],
                defaults={**record, "created_by": user, "updated_by": user},
            )
            label = "Creado" if created else "Ya existe"
            self.stdout.write(f"{label}: {record['document_number']}")
