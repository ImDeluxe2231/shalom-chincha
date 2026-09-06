from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from .models import User


@override_settings(DEBUG=True, PRODUCTION=False)
class DemoUserSecurityTests(TestCase):
    def test_creates_random_passwords_and_preserves_existing_users(self):
        with patch("accounts.management.commands.create_demo_users.secrets.token_urlsafe", side_effect=["clave-aleatoria-1", "clave-aleatoria-2", "clave-aleatoria-3"]):
            call_command("create_demo_users", stdout=StringIO())
        admin = User.objects.get(username="admin")
        self.assertTrue(admin.check_password("clave-aleatoria-1"))
        self.assertTrue(admin.is_superuser)
        call_command("create_demo_users", stdout=StringIO())
        admin.refresh_from_db()
        self.assertTrue(admin.check_password("clave-aleatoria-1"))
        self.assertEqual(User.objects.count(), 3)

    @override_settings(DEBUG=False, PRODUCTION=True)
    def test_demo_users_are_blocked_in_production(self):
        with self.assertRaises(CommandError):
            call_command("create_demo_users", stdout=StringIO())
        self.assertFalse(User.objects.exists())

    @override_settings(DEBUG=False, PRODUCTION=True)
    def test_massive_demo_data_is_blocked_in_production(self):
        with self.assertRaises(CommandError):
            call_command("cargar_datos_demo", stdout=StringIO())
