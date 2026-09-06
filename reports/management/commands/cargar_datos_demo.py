import secrets
from django.conf import settings
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from customers.models import Customer
from operations.models import Delivery, Incident, IncidentAction
from shipments.models import Agency, Package, Shipment, ShipmentStatus, TrackingEvent, WarehouseLocation


DEMO_MARKER = "[DEMO-MASIVO-2027]"


class Command(BaseCommand):
    help = "Carga datos demostrativos realistas sin eliminar los registros existentes."

    FIRST_NAMES = [
        "Andrea", "Carlos", "Lucía", "Diego", "Valeria", "Jorge", "María", "José",
        "Camila", "Renato", "Daniela", "Luis", "Fiorella", "Miguel", "Paola", "Bruno",
        "Alessandra", "Fernando", "Rosa", "Marco", "Diana", "Ángel", "Katherine", "Sergio",
    ]
    LAST_NAMES = [
        "Quispe Huamán", "Mendoza Rojas", "Torres Salazar", "Ramos García", "Flores Castillo",
        "Cárdenas Vega", "Pérez León", "Navarro Soto", "Chávez Medina", "Palomino Cruz",
        "Gutiérrez Peña", "Espinoza Díaz", "Vargas Herrera", "Reyes Campos", "López Cabrera",
    ]
    BUSINESSES = [
        "Comercial Andina", "Distribuidora del Sur", "Textiles Chincha", "Inversiones Pacífico",
        "Agroexportadora San José", "Servicios Generales Nazca", "Importaciones Sol del Perú",
        "Ferretería Central", "Corporación Valle Grande", "Bodegas del Carmen",
    ]
    CONTENTS = [
        ("PACKAGE", "Prendas de vestir", False), ("PACKAGE", "Artículos para el hogar", False),
        ("PARCEL", "Productos artesanales", False), ("PACKAGE", "Accesorios electrónicos", True),
        ("ENVELOPE", "Documentación empresarial", False), ("CARGO", "Repuestos de maquinaria", False),
        ("PARCEL", "Productos agrícolas procesados", False), ("PACKAGE", "Material educativo", False),
        ("PACKAGE", "Cosméticos sellados", True), ("PARCEL", "Calzado y accesorios", False),
    ]
    STATUS_PATTERN = [
        "REGISTERED", "RECEIVED", "IN_WAREHOUSE", "IN_WAREHOUSE", "DISPATCHED",
        "IN_TRANSIT", "IN_TRANSIT", "IN_TRANSIT", "AT_DESTINATION", "READY_PICKUP",
        "READY_PICKUP", "DELIVERED", "DELIVERED", "DELIVERED", "DELIVERED", "DELIVERED",
        "INCIDENT", "CANCELED",
    ]
    NORMAL_FLOW = [
        "REGISTERED", "RECEIVED", "IN_WAREHOUSE", "DISPATCHED",
        "IN_TRANSIT", "AT_DESTINATION", "READY_PICKUP", "DELIVERED",
    ]
    EVENT_NOTES = {
        "REGISTERED": "Orden registrada y comprobante emitido en ventanilla.",
        "RECEIVED": "Bultos recibidos y verificados en la agencia de origen.",
        "IN_WAREHOUSE": "Envío clasificado y ubicado en el almacén de origen.",
        "DISPATCHED": "Carga incluida en manifiesto y despachada hacia su destino.",
        "IN_TRANSIT": "Unidad en recorrido interprovincial según programación.",
        "AT_DESTINATION": "Envío recibido y descargado en la agencia de destino.",
        "READY_PICKUP": "Bultos verificados y disponibles para entrega al destinatario.",
        "DELIVERED": "Entrega confirmada mediante validación de identidad y código.",
        "CANCELED": "Orden anulada por solicitud administrativa documentada.",
        "INCIDENT": "Operación temporalmente detenida para atender una incidencia.",
    }

    def add_arguments(self, parser):
        parser.add_argument("--clientes", type=int, default=140, help="Cantidad de clientes demostrativos (predeterminado: 140).")
        parser.add_argument("--envios", type=int, default=360, help="Cantidad de envíos demostrativos (predeterminado: 360).")
        parser.add_argument("--dias", type=int, default=120, help="Periodo histórico en días (predeterminado: 120).")
        parser.add_argument("--semilla", type=int, default=2027, help="Semilla para obtener resultados reproducibles.")
        parser.add_argument("--agregar", action="store_true", help="Agrega otro lote de envíos reutilizando los clientes existentes.")

    def handle(self, *args, **options):
        if not settings.DEBUG or getattr(settings, "PRODUCTION", False):
            raise CommandError("La carga demostrativa solo está disponible en desarrollo local.")
        client_count = options["clientes"]
        shipment_count = options["envios"]
        days = options["dias"]
        if client_count < 20 or shipment_count < 18 or days < 30 or days > 730:
            raise CommandError("Usa al menos 20 clientes, 18 envíos y un periodo de 30 a 730 días.")
        existing = Shipment.objects.filter(notes__contains=DEMO_MARKER).count()
        if existing and not options["agregar"]:
            self.stdout.write(self.style.WARNING(
                f"La carga masiva ya existe ({existing} envíos). No se duplicaron datos. "
                "Usa --agregar únicamente si necesitas otro lote."
            ))
            return

        rng = random.Random(options["semilla"] + existing)
        users = self._ensure_users()
        agencies = list(Agency.objects.filter(is_active=True))
        statuses = {item.code: item for item in ShipmentStatus.objects.all()}
        required = set(self.NORMAL_FLOW) | {"INCIDENT", "CANCELED"}
        if len(agencies) < 2 or not required.issubset(statuses):
            raise CommandError("Ejecuta primero: python manage.py migrate")

        with transaction.atomic():
            customers = self._create_customers(client_count, agencies, users["admin"], rng, options["semilla"])
            summary = self._create_shipments(
                shipment_count, days, customers, agencies, statuses, users, rng
            )

        self.stdout.write(self.style.SUCCESS("Carga demostrativa completada correctamente."))
        self.stdout.write(
            f"Clientes disponibles: {len(customers)} | Envíos nuevos: {summary['shipments']} | "
            f"Entregas: {summary['deliveries']} | Incidencias: {summary['incidents']} | "
            f"Eventos de seguimiento: {summary['events']}"
        )
        self.stdout.write("Abre el dashboard y mantén el filtro predeterminado de los últimos 30 días.")

    def _ensure_users(self):
        definitions = [
            ("admin", "Administrador", "Demo", User.Role.ADMIN),
            ("ventanilla", "Personal", "Administrativo", User.Role.ADMINISTRATIVE),
            ("almacen", "Personal", "Operativo", User.Role.OPERATIONAL),
        ]
        result = {}
        for username, first_name, last_name, role in definitions:
            user = User.objects.filter(role=role, is_active=True).first()
            if user is None:
                password = secrets.token_urlsafe(24)
                user = User.objects.create_user(
                    username=username, password=password, first_name=first_name,
                    last_name=last_name, role=role,
                )
                self.stdout.write(f"Usuario demo creado: {user.username} | Contraseña: {password}")
            result[{User.Role.ADMIN: "admin", User.Role.ADMINISTRATIVE: "office", User.Role.OPERATIONAL: "operator"}[role]] = user
        return result

    def _create_customers(self, amount, agencies, user, rng, seed):
        created_customers = []
        base_person = 81_000_000 + (seed % 100) * 1_000
        base_company = 205_000_000_00 + (seed % 100) * 10_000
        for index in range(amount):
            agency = agencies[index % len(agencies)]
            phone = f"9{((seed * 1000 + index) % 100_000_000):08d}"
            if index % 10 == 0:
                document = str(base_company + index)
                record = {
                    "customer_type": Customer.CustomerType.BUSINESS,
                    "document_type": Customer.DocumentType.RUC,
                    "business_name": f"{self.BUSINESSES[(index // 10) % len(self.BUSINESSES)]} S.A.C.",
                    "email": f"pedidos{index}@empresa-demo.test",
                }
            else:
                document = str(base_person + index)
                first_name = self.FIRST_NAMES[index % len(self.FIRST_NAMES)]
                last_name = self.LAST_NAMES[(index * 3) % len(self.LAST_NAMES)]
                record = {
                    "customer_type": Customer.CustomerType.PERSON,
                    "document_type": Customer.DocumentType.DNI,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": f"cliente{index}@correo-demo.test" if index % 3 == 0 else "",
                }
            customer, _ = Customer.objects.get_or_create(
                document_number=document,
                defaults={
                    **record,
                    "phone": phone,
                    "department": agency.department,
                    "province": agency.province,
                    "district": agency.district,
                    "address": f"{rng.choice(['Av.', 'Calle', 'Jr.'])} {rng.choice(['Los Laureles', 'San Martín', 'El Carmen', 'Las Palmeras', '28 de Julio'])} {100 + index}",
                    "reference": rng.choice(["Cerca de la plaza", "Frente al mercado", "A una cuadra del parque", "Puerta de color blanco", ""]),
                    "notes": f"Cliente generado para demostración académica {DEMO_MARKER}",
                    "created_by": user,
                    "updated_by": user,
                },
            )
            created_customers.append(customer)
        return created_customers

    def _create_shipments(self, amount, days, customers, agencies, statuses, users, rng):
        now = timezone.now()
        status_plan = [self.STATUS_PATTERN[index % len(self.STATUS_PATTERN)] for index in range(amount)]
        rng.shuffle(status_plan)
        summary = {"shipments": 0, "deliveries": 0, "incidents": 0, "events": 0}
        for index, status_code in enumerate(status_plan):
            day_offset = rng.randint(0, days - 1)
            if status_code == "DELIVERED" and day_offset < 2:
                day_offset = rng.randint(2, min(days - 1, 8))
            created_at = now - timedelta(days=day_offset, hours=rng.randint(0, 18), minutes=rng.randint(0, 59))
            origin, destination = rng.sample(agencies, 2)
            sender, recipient = rng.sample(customers, 2)
            transport = Shipment.TransportMode.AIR if (
                origin.supports_air and destination.supports_air and rng.random() < .22
            ) else Shipment.TransportMode.GROUND
            service = rng.choices(
                [Shipment.ServiceType.AGENCY, Shipment.ServiceType.ADDRESS], weights=[76, 24], k=1
            )[0]
            payer = rng.choice([Shipment.Payer.SENDER, Shipment.Payer.RECIPIENT])
            timing = Shipment.PaymentTiming.ORIGIN if payer == Shipment.Payer.SENDER else Shipment.PaymentTiming.DESTINATION
            paid_probability = .96 if status_code == "DELIVERED" else .68
            payment = Shipment.PaymentStatus.PAID if rng.random() < paid_probability else Shipment.PaymentStatus.PENDING
            shipping_cost = Decimal(rng.randrange(1800, 15501, 50)) / 100
            insurance = Decimal(rng.choice([0, 0, 0, 300, 500, 800, 1200])) / 100
            discount = Decimal(rng.choice([0, 0, 0, 200, 500])) / 100
            current_agency = destination if status_code in {"AT_DESTINATION", "READY_PICKUP", "DELIVERED"} else origin
            location = None
            if status_code == "IN_WAREHOUSE":
                location = WarehouseLocation.objects.filter(agency=origin, is_active=True).first()
            shipment = Shipment.objects.create(
                sender=sender, recipient=recipient, origin=origin, destination=destination,
                transport_mode=transport, service_type=service, payer=payer, payment_timing=timing,
                payment_status=payment, shipping_cost=shipping_cost, insurance_cost=insurance,
                discount=min(discount, shipping_cost + insurance),
                estimated_delivery_date=created_at.date() + timedelta(days=rng.randint(2, 7)),
                current_status=statuses[status_code], current_agency=current_agency,
                current_location=location,
                status_changed_at=min(now, created_at + timedelta(days=max(1, day_offset // 2))),
                notes=f"Operación demostrativa para análisis institucional {DEMO_MARKER}",
                cancel_reason="Solicitud del remitente antes del despacho." if status_code == "CANCELED" else "",
                created_by=users["office"], updated_by=users["operator"],
            )
            Shipment.objects.filter(pk=shipment.pk).update(created_at=created_at, updated_at=min(now, created_at + timedelta(hours=6)))
            package_total = self._create_packages(shipment, rng)

            if status_code == "INCIDENT":
                previous_code = rng.choice(["RECEIVED", "IN_WAREHOUSE", "DISPATCHED", "IN_TRANSIT", "AT_DESTINATION"])
                event_count = self._create_tracking(shipment, previous_code, statuses, created_at, now, users["operator"], rng)
                incident = self._create_incident(
                    shipment, statuses[previous_code], current_agency, created_at, now,
                    users, rng, resolved=False,
                )
                event = TrackingEvent.objects.create(
                    shipment=shipment, previous_status=statuses[previous_code], status=statuses["INCIDENT"],
                    agency=current_agency, notes=self.EVENT_NOTES["INCIDENT"], created_by=users["operator"],
                )
                TrackingEvent.objects.filter(pk=event.pk).update(created_at=incident.reported_at)
                summary["incidents"] += 1
                summary["events"] += event_count + 1
            else:
                event_count = self._create_tracking(shipment, status_code, statuses, created_at, now, users["operator"], rng)
                summary["events"] += event_count
                if status_code == "DELIVERED":
                    self._create_delivery(shipment, recipient, package_total, created_at, now, users["operator"], rng)
                    summary["deliveries"] += 1
                if status_code not in {"REGISTERED", "CANCELED"} and index % 9 == 0:
                    previous = statuses[rng.choice(["RECEIVED", "IN_WAREHOUSE", "DISPATCHED", "IN_TRANSIT"])]
                    self._create_incident(shipment, previous, origin, created_at, now, users, rng, resolved=True)
                    summary["incidents"] += 1
            summary["shipments"] += 1
        return summary

    def _create_packages(self, shipment, rng):
        total = 0
        for _ in range(1 if rng.random() < .72 else 2):
            package_type, description, fragile = rng.choice(self.CONTENTS)
            quantity = rng.choice([1, 1, 1, 2, 2, 3])
            total += quantity
            Package.objects.create(
                shipment=shipment, package_type=package_type, description=description,
                quantity=quantity, weight=Decimal(rng.randrange(50, 1801)) / 100,
                length=Decimal(rng.randrange(18, 81)), width=Decimal(rng.randrange(15, 61)),
                height=Decimal(rng.randrange(8, 51)), declared_value=Decimal(rng.randrange(3000, 90001, 500)) / 100,
                is_fragile=fragile, observations="Manipular con cuidado." if fragile else "",
            )
        return total

    def _create_tracking(self, shipment, target_code, statuses, start, now, user, rng):
        if target_code == "CANCELED":
            flow = ["REGISTERED", "CANCELED"]
        else:
            flow = self.NORMAL_FLOW[:self.NORMAL_FLOW.index(target_code) + 1]
        available_hours = max(2, int((now - start).total_seconds() // 3600))
        step = max(1, available_hours // max(1, len(flow)))
        previous = None
        for position, code in enumerate(flow):
            agency = shipment.destination if code in {"AT_DESTINATION", "READY_PICKUP", "DELIVERED"} else shipment.origin
            location = WarehouseLocation.objects.filter(agency=agency, is_active=True).first() if code == "IN_WAREHOUSE" else None
            event = TrackingEvent.objects.create(
                shipment=shipment, status=statuses[code], previous_status=statuses.get(previous) if previous else None,
                agency=agency, location=location,
                transport_reference=f"MAN-{start:%m%d}-{rng.randint(100, 999)}" if code == "DISPATCHED" else "",
                notes=self.EVENT_NOTES[code], created_by=user, is_system=code == "REGISTERED",
            )
            event_time = min(now, start + timedelta(hours=position * step + rng.randint(0, max(1, step))))
            TrackingEvent.objects.filter(pk=event.pk).update(created_at=event_time)
            previous = code
        return len(flow)

    def _create_delivery(self, shipment, recipient, package_total, start, now, user, rng):
        delivered_at = min(now, start + timedelta(days=rng.randint(1, 5), hours=rng.randint(1, 12)))
        if recipient.customer_type == Customer.CustomerType.PERSON:
            receiver_type = Delivery.ReceiverType.RECIPIENT
            name = recipient.display_name
            document = recipient.document_number
            relationship = ""
            verification = Delivery.VerificationMethod.DOCUMENT_CODE
        else:
            receiver_type = Delivery.ReceiverType.AUTHORIZED
            name = f"{rng.choice(self.FIRST_NAMES)} {rng.choice(self.LAST_NAMES)}"
            document = f"77{rng.randint(100000, 999999)}"
            relationship = "Representante de la empresa"
            verification = Delivery.VerificationMethod.AUTHORIZATION
        observed = rng.random() < .09
        delivery = Delivery.objects.create(
            shipment=shipment, agency=shipment.destination, delivery_method=shipment.service_type,
            receiver_type=receiver_type, receiver_name=name, receiver_document_type=Delivery.DocumentType.DNI,
            receiver_document_number=document, receiver_phone=f"9{rng.randint(10000000, 99999999)}",
            relationship=relationship, verification_method=verification,
            package_condition=Delivery.PackageCondition.OBSERVED if observed else Delivery.PackageCondition.CONFORMING,
            condition_notes="Embalaje exterior con una observación menor; contenido recibido conforme." if observed else "",
            packages_delivered=package_total, payment_confirmed=True,
            notes=f"Constancia generada para demostración {DEMO_MARKER}",
            delivered_by=user, delivered_at=delivered_at,
        )
        Delivery.objects.filter(pk=delivery.pk).update(created_at=delivered_at)
        if shipment.payment_status != Shipment.PaymentStatus.PAID:
            Shipment.objects.filter(pk=shipment.pk).update(payment_status=Shipment.PaymentStatus.PAID)

    def _create_incident(self, shipment, previous_status, agency, start, now, users, rng, resolved):
        types = list(Incident.IncidentType.values)
        severities = [Incident.Severity.LOW, Incident.Severity.MEDIUM, Incident.Severity.HIGH, Incident.Severity.CRITICAL]
        incident_type = rng.choice(types)
        severity = rng.choices(severities, weights=[28, 42, 24, 6], k=1)[0]
        reported_at = min(now, start + timedelta(hours=rng.randint(4, 36)))
        status = Incident.Status.RESOLVED if resolved else rng.choice([Incident.Status.OPEN, Incident.Status.IN_REVIEW])
        incident = Incident.objects.create(
            shipment=shipment, previous_status=previous_status, agency=agency,
            incident_type=incident_type, severity=severity, status=status,
            description=f"Se registró una observación de tipo {dict(Incident.IncidentType.choices)[incident_type].lower()} durante la operación. {DEMO_MARKER}",
            public_message="El envío presenta una observación operativa y está siendo atendido.",
            assigned_to=users["operator"] if status != Incident.Status.OPEN else None,
            resolution="Se verificaron los bultos y se aplicó el procedimiento operativo correspondiente." if resolved else "",
            reported_by=users["operator"], resolved_by=users["admin"] if resolved else None,
            resolved_at=min(now, reported_at + timedelta(hours=rng.randint(3, 30))) if resolved else None,
        )
        Incident.objects.filter(pk=incident.pk).update(reported_at=reported_at, updated_at=incident.resolved_at or reported_at)
        incident.refresh_from_db()
        actions = [
            (IncidentAction.Action.REPORTED, "Incidencia reportada y registrada para evaluación.", users["operator"], reported_at),
        ]
        if status != Incident.Status.OPEN:
            actions.append((IncidentAction.Action.ASSIGNED, "Caso asignado al responsable operativo.", users["admin"], min(now, reported_at + timedelta(hours=1))))
        if resolved:
            actions.append((IncidentAction.Action.RESOLVED, incident.resolution, users["admin"], incident.resolved_at))
        for action_code, notes, actor, moment in actions:
            action = IncidentAction.objects.create(incident=incident, action=action_code, notes=notes, performed_by=actor)
            IncidentAction.objects.filter(pk=action.pk).update(created_at=moment)
        return incident
