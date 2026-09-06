from django.urls import path

from . import views


urlpatterns = [
    path("entregas/", views.delivery_dashboard, name="delivery_dashboard"),
    path("entregas/historial/", views.delivery_history, name="delivery_history"),
    path("entregas/registrar/<int:shipment_id>/", views.delivery_create, name="delivery_create"),
    path("entregas/<int:pk>/", views.delivery_detail, name="delivery_detail"),
    path("entregas/<int:pk>/comprobante/", views.delivery_receipt, name="delivery_receipt"),
    path("entregas/verificar/<uuid:verification_code>/", views.delivery_verify, name="delivery_verify"),
    path("incidencias/", views.incident_list, name="incident_list"),
    path("incidencias/reportar/<int:shipment_id>/", views.incident_create, name="incident_create"),
    path("incidencias/<int:pk>/", views.incident_detail, name="incident_detail"),
    path("incidencias/<int:pk>/evidencia/", views.incident_evidence, name="incident_evidence"),
    path("incidencias/<int:pk>/revisar/", views.incident_review, name="incident_review"),
    path("incidencias/<int:pk>/resolver/", views.incident_resolve, name="incident_resolve"),
]
