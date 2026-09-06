from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (
            "Datos de Shalom Chincha",
            {
                "fields": (
                    "role",
                    "document_type",
                    "document_number",
                    "phone",
                    "must_change_password",
                    "created_by",
                )
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Datos de Shalom Chincha",
            {"fields": ("role", "document_type", "document_number", "phone")},
        ),
    )
    list_display = ("username", "first_name", "last_name", "role", "is_active", "last_login")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "first_name", "last_name", "document_number")
