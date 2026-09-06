from django.test import TestCase
from django.urls import reverse

from .models import User


class AuthenticationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_test", password="Prueba2027!", role=User.Role.ADMIN
        )
        self.operator = User.objects.create_user(
            username="operator_test", password="Prueba2027!", role=User.Role.OPERATIONAL
        )

    def test_login_redirects_to_dashboard(self):
        response = self.client.post(
            reverse("login"), {"username": "operator_test", "password": "Prueba2027!"}
        )
        self.assertRedirects(response, reverse("dashboard"))

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_operator_cannot_manage_users(self):
        self.client.force_login(self.operator)
        response = self.client.get(reverse("user_list"))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_manage_users(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("user_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "operator_test")

    def test_admin_can_create_user(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("user_create"),
            {
                "username": "ventanilla_test",
                "first_name": "Ana",
                "last_name": "Prueba",
                "email": "ana@example.com",
                "document_type": "DNI",
                "document_number": "70123456",
                "phone": "987654321",
                "role": User.Role.ADMINISTRATIVE,
                "is_active": "on",
                "password1": "Segura2027!",
                "password2": "Segura2027!",
            },
        )
        self.assertRedirects(response, reverse("user_list"))
        self.assertTrue(User.objects.filter(username="ventanilla_test").exists())

    def test_admin_cannot_deactivate_self(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("user_toggle_active", args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
