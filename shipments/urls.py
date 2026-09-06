from django.urls import path

from . import views

urlpatterns = [
    path("", views.shipment_list, name="shipment_list"),
    path("nuevo/", views.shipment_create, name="shipment_create"),
    path("agencias/", views.agency_list, name="agency_list"),
    path("agencias/nueva/", views.agency_create, name="agency_create"),
    path("agencias/<int:pk>/editar/", views.agency_update, name="agency_update"),
    path("agencias/<int:pk>/estado/", views.agency_toggle_active, name="agency_toggle_active"),
    path("<int:pk>/", views.shipment_detail, name="shipment_detail"),
    path("<int:pk>/editar/", views.shipment_update, name="shipment_update"),
    path("<int:pk>/anular/", views.shipment_cancel, name="shipment_cancel"),
    path("<int:pk>/comprobante/", views.shipment_ticket, name="shipment_ticket"),
]
