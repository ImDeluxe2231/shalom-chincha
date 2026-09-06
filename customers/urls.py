from django.urls import path

from . import views

urlpatterns = [
    path("", views.customer_list, name="customer_list"),
    path("nuevo/", views.customer_create, name="customer_create"),
    path("<int:pk>/", views.customer_detail, name="customer_detail"),
    path("<int:pk>/editar/", views.customer_update, name="customer_update"),
    path("<int:pk>/estado/", views.customer_toggle_active, name="customer_toggle_active"),
]
