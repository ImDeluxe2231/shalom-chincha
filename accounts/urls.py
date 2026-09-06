from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import LoginForm
from . import views

urlpatterns = [
    path(
        "ingresar/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=LoginForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("salir/", auth_views.LogoutView.as_view(), name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("mi-perfil/", views.profile, name="profile"),
    path(
        "cambiar-clave/",
        auth_views.PasswordChangeView.as_view(
            template_name="registration/password_change_form.html",
            success_url="/clave-actualizada/",
        ),
        name="password_change",
    ),
    path(
        "clave-actualizada/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="registration/password_change_done.html"
        ),
        name="password_change_done",
    ),
    path("usuarios/", views.user_list, name="user_list"),
    path("usuarios/nuevo/", views.user_create, name="user_create"),
    path("usuarios/<int:pk>/editar/", views.user_update, name="user_update"),
    path("usuarios/<int:pk>/estado/", views.user_toggle_active, name="user_toggle_active"),
]
