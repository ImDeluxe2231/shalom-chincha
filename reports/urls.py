from django.urls import path

from . import views


urlpatterns = [
    path("", views.report_center, name="report_center"),
    path("exportar/<str:report_type>/<str:file_format>/", views.report_export, name="report_export"),
]
