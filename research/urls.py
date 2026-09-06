from django.urls import path

from . import views


urlpatterns = [
    path("", views.validation_dashboard, name="validation_dashboard"),
    path("trazabilidad/nueva/", views.traceability_create, name="research_traceability_create"),
    path("tiempos/nuevo/", views.response_time_create, name="research_response_time_create"),
    path("encuestas/nueva/", views.survey_create, name="research_survey_create"),
    path("exportar/", views.export_validation_data, name="research_export"),
]
