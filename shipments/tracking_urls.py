from django.urls import path

from . import tracking_views


urlpatterns = [
    path("", tracking_views.public_tracking, name="public_tracking"),
    path("operaciones/", tracking_views.tracking_dashboard, name="tracking_dashboard"),
    path("operaciones/<int:pk>/", tracking_views.tracking_detail, name="tracking_detail"),
    path("operaciones/<int:pk>/actualizar/<str:target_code>/", tracking_views.tracking_transition, name="tracking_transition"),
    path("ubicaciones/", tracking_views.warehouse_location_list, name="warehouse_location_list"),
    path("ubicaciones/nueva/", tracking_views.warehouse_location_create, name="warehouse_location_create"),
    path("ubicaciones/<int:pk>/editar/", tracking_views.warehouse_location_update, name="warehouse_location_update"),
]
