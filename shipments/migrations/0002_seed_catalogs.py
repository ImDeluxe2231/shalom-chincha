from django.db import migrations


STATUSES = [
    ("REGISTERED", "Registrado", "Envío registrado en ventanilla.", "#2563EB", 10, False),
    ("RECEIVED", "Recibido en agencia", "Paquete verificado y recibido físicamente.", "#0EA5E9", 20, False),
    ("IN_WAREHOUSE", "En almacén de origen", "Paquete ubicado en almacén para despacho.", "#7C3AED", 30, False),
    ("DISPATCHED", "Despachado", "Envío asignado a una salida.", "#8B5CF6", 40, False),
    ("IN_TRANSIT", "En tránsito", "Envío en traslado hacia su destino.", "#F59E0B", 50, False),
    ("AT_DESTINATION", "Recibido en destino", "Paquete recibido en la agencia de destino.", "#F97316", 60, False),
    ("READY_PICKUP", "Disponible para recojo", "El destinatario puede recoger el envío.", "#10B981", 70, False),
    ("DELIVERED", "Entregado", "Envío entregado al destinatario.", "#15803D", 80, True),
    ("INCIDENT", "Con incidencia", "El envío requiere revisión.", "#DC2626", 90, False),
    ("CANCELED", "Anulado", "Envío anulado por un administrador.", "#64748B", 100, True),
]

AGENCIES = [
    ("CHI", "Shalom Chincha", "Ica", "Chincha", "Chincha Alta", True, False),
    ("LIM", "Shalom Lima", "Lima", "Lima", "La Victoria", True, True),
    ("ICA", "Shalom Ica", "Ica", "Ica", "Ica", True, False),
    ("AQP", "Shalom Arequipa", "Arequipa", "Arequipa", "Arequipa", True, True),
    ("AYA", "Shalom Ayacucho", "Ayacucho", "Huamanga", "Ayacucho", True, False),
    ("CUS", "Shalom Cusco", "Cusco", "Cusco", "Cusco", True, True),
]


def seed(apps, schema_editor):
    Status = apps.get_model("shipments", "ShipmentStatus")
    Agency = apps.get_model("shipments", "Agency")
    for code, name, description, color, order, terminal in STATUSES:
        Status.objects.update_or_create(code=code, defaults={"name": name, "description": description, "color": color, "sort_order": order, "is_terminal": terminal})
    for code, name, department, province, district, ground, air in AGENCIES:
        Agency.objects.update_or_create(code=code, defaults={"name": name, "department": department, "province": province, "district": district, "address": "Por configurar", "supports_ground": ground, "supports_air": air, "is_active": True})


def unseed(apps, schema_editor):
    apps.get_model("shipments", "ShipmentStatus").objects.filter(code__in=[row[0] for row in STATUSES]).delete()
    apps.get_model("shipments", "Agency").objects.filter(code__in=[row[0] for row in AGENCIES]).delete()


class Migration(migrations.Migration):
    dependencies = [("shipments", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
