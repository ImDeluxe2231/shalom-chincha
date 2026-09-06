from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin-django/", admin.site.urls),
    path("seguimiento/", include("shipments.tracking_urls")),
    path("envios/", include("shipments.urls")),
    path("clientes/", include("customers.urls")),
    path("reportes/", include("reports.urls")),
    path("validacion/", include("research.urls")),
    path("", include("operations.urls")),
    path("", include("accounts.urls")),
]
