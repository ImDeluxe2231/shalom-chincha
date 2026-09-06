from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Customer


class CustomerModelTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin_customer", password="Prueba2027!", role=User.Role.ADMIN)

    def customer(self, **changes):
        data = {
            "customer_type": Customer.CustomerType.PERSON,
            "document_type": Customer.DocumentType.DNI,
            "document_number": "71234567",
            "first_name": "Rosa",
            "last_name": "Quispe Flores",
            "phone": "987654321",
            "district": "Chincha Alta",
            "address": "Av. Principal 123",
            "created_by": self.admin,
            "updated_by": self.admin,
        }
        data.update(changes)
        return Customer(**data)

    def test_valid_person_can_be_saved(self):
        customer = self.customer()
        customer.save()
        self.assertEqual(customer.display_name, "Rosa Quispe Flores")

    def test_invalid_dni_is_rejected(self):
        customer = self.customer(document_number="123")
        with self.assertRaises(ValidationError):
            customer.save()

    def test_business_requires_ruc_and_business_name(self):
        customer = self.customer(customer_type=Customer.CustomerType.BUSINESS)
        with self.assertRaises(ValidationError):
            customer.save()


class CustomerViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin2", password="Prueba2027!", role=User.Role.ADMIN)
        self.administrative = User.objects.create_user(username="office", password="Prueba2027!", role=User.Role.ADMINISTRATIVE)
        self.operator = User.objects.create_user(username="warehouse", password="Prueba2027!", role=User.Role.OPERATIONAL)
        self.customer = Customer.objects.create(
            customer_type=Customer.CustomerType.PERSON,
            document_type=Customer.DocumentType.DNI,
            document_number="70112233",
            first_name="Luis",
            last_name="Torres Díaz",
            phone="955666777",
            district="Pueblo Nuevo",
            address="Calle Comercio 456",
            created_by=self.admin,
            updated_by=self.admin,
        )

    def valid_form_data(self):
        return {
            "customer_type": "PERSON",
            "document_type": "DNI",
            "document_number": "72345678",
            "first_name": "María",
            "last_name": "Ramos Peña",
            "business_name": "",
            "phone": "966777888",
            "secondary_phone": "",
            "email": "maria@example.com",
            "department": "Ica",
            "province": "Chincha",
            "district": "Sunampe",
            "address": "Jr. Los Pinos 120",
            "reference": "Frente al parque",
            "notes": "",
            "is_active": "on",
        }

    def test_operator_can_view_but_cannot_create(self):
        self.client.force_login(self.operator)
        self.assertEqual(self.client.get(reverse("customer_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("customer_create")).status_code, 403)

    def test_administrative_can_create_customer(self):
        self.client.force_login(self.administrative)
        response = self.client.post(reverse("customer_create"), self.valid_form_data())
        created = Customer.objects.get(document_number="72345678")
        self.assertRedirects(response, reverse("customer_detail", args=[created.pk]))

    def test_search_by_document(self):
        self.client.force_login(self.operator)
        response = self.client.get(reverse("customer_list"), {"q": "70112233", "status": "all"})
        self.assertContains(response, "Luis Torres Díaz")

    def test_duplicate_document_is_rejected(self):
        self.client.force_login(self.administrative)
        data = self.valid_form_data()
        data["document_number"] = self.customer.document_number
        response = self.client.post(reverse("customer_create"), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Este documento ya pertenece")
