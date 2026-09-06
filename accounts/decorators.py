from functools import wraps

from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required


def admin_role_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_admin_role:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapped


def administrative_role_required(view_func):
    """Permite escribir a administradores y personal de ventanilla."""

    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        allowed_roles = {"ADMIN", "ADMINISTRATIVE"}
        if not (request.user.is_superuser or request.user.role in allowed_roles):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapped


def operational_role_required(view_func):
    """Permite operaciones de almacén a administradores y personal operativo."""

    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        allowed_roles = {"ADMIN", "OPERATIONAL"}
        if not (request.user.is_superuser or request.user.role in allowed_roles):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapped
