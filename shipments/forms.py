from decimal import Decimal

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.db import models
from django.utils import timezone

from customers.models import Customer

from .models import Agency, Package, Shipment, WarehouseLocation


class StyledModelForm(forms.ModelForm):
    def apply_styles(self):
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"
            field.widget.attrs.setdefault("placeholder", field.label)


class AgencyForm(StyledModelForm):
    class Meta:
        model = Agency
        fields = ("code", "name", "department", "province", "district", "address", "supports_ground", "supports_air", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()
        if self.instance.pk:
            self.fields["code"].disabled = True
            self.fields["code"].help_text = "El código no puede cambiar porque identifica las órdenes emitidas."

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("supports_ground") and not cleaned_data.get("supports_air"):
            raise forms.ValidationError("Habilita al menos una modalidad: terrestre o aérea.")
        return cleaned_data


class ShipmentForm(StyledModelForm):
    class Meta:
        model = Shipment
        fields = (
            "sender", "recipient", "origin", "destination", "transport_mode", "service_type",
            "payer", "payment_timing", "payment_status", "shipping_cost", "insurance_cost",
            "discount", "estimated_delivery_date", "notes",
        )
        widgets = {
            "estimated_delivery_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "shipping_cost": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
            "insurance_cost": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
            "discount": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()
        active_customers = Customer.objects.filter(is_active=True)
        active_agencies = Agency.objects.filter(is_active=True)
        if self.instance.pk:
            active_customers = Customer.objects.filter(models.Q(is_active=True) | models.Q(pk__in=[self.instance.sender_id, self.instance.recipient_id]))
            active_agencies = Agency.objects.filter(models.Q(is_active=True) | models.Q(pk__in=[self.instance.origin_id, self.instance.destination_id]))
        self.fields["sender"].queryset = active_customers
        self.fields["recipient"].queryset = active_customers
        self.fields["origin"].queryset = active_agencies
        self.fields["destination"].queryset = active_agencies
        self.fields["sender"].empty_label = "Selecciona al remitente"
        self.fields["recipient"].empty_label = "Selecciona al destinatario"
        self.fields["origin"].empty_label = "Selecciona la agencia de origen"
        self.fields["destination"].empty_label = "Selecciona la agencia de destino"
        if self.instance.pk:
            self.fields["origin"].disabled = True
            self.fields["origin"].help_text = "El origen queda fijo porque forma parte del número de orden."

    def clean_estimated_delivery_date(self):
        delivery_date = self.cleaned_data.get("estimated_delivery_date")
        if delivery_date and not self.instance.pk and delivery_date < timezone.localdate():
            raise forms.ValidationError("La fecha estimada no puede estar en el pasado.")
        return delivery_date


class PackageForm(StyledModelForm):
    class Meta:
        model = Package
        fields = ("package_type", "description", "quantity", "weight", "length", "width", "height", "declared_value", "is_fragile", "observations")
        widgets = {
            "quantity": forms.NumberInput(attrs={"min": "1", "step": "1"}),
            "weight": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
            "length": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
            "width": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
            "height": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
            "declared_value": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()


class BasePackageFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        valid_packages = 0
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get("DELETE", False):
                valid_packages += 1
        if valid_packages < 1:
            raise forms.ValidationError("El envío debe contener al menos un paquete.")


PackageFormSet = inlineformset_factory(
    Shipment,
    Package,
    form=PackageForm,
    formset=BasePackageFormSet,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class CancellationForm(forms.Form):
    reason = forms.CharField(
        label="Motivo de anulación",
        min_length=10,
        max_length=300,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Explica por qué se anula el envío"}),
    )


class WarehouseLocationForm(StyledModelForm):
    class Meta:
        model = WarehouseLocation
        fields = ("agency", "code", "name", "zone", "rack", "level", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()
        self.fields["agency"].queryset = Agency.objects.filter(is_active=True)
        if self.instance.pk:
            self.fields["agency"].queryset = Agency.objects.filter(models.Q(is_active=True) | models.Q(pk=self.instance.agency_id))
            self.fields["agency"].disabled = True
            self.fields["code"].disabled = True
            self.fields["agency"].help_text = "La agencia queda fija para conservar el historial operativo."
            self.fields["code"].help_text = "El código queda fijo porque puede estar asociado a movimientos existentes."


class OperationalTransitionForm(forms.Form):
    location = forms.ModelChoiceField(
        label="Ubicación de almacén",
        queryset=WarehouseLocation.objects.none(),
        required=False,
        empty_label="Selecciona una ubicación",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    transport_reference = forms.CharField(
        label="Manifiesto, vehículo o vuelo",
        max_length=80,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej. MAN-2027-0042 / ABC-123"}),
    )
    notes = forms.CharField(
        label="Observación operativa",
        max_length=300,
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Detalle adicional del movimiento"}),
    )

    def __init__(self, *args, shipment, target_code, **kwargs):
        super().__init__(*args, **kwargs)
        self.shipment = shipment
        self.target_code = target_code
        agency = shipment.destination if target_code == "AT_DESTINATION" else shipment.origin
        self.fields["location"].queryset = WarehouseLocation.objects.filter(agency=agency, is_active=True)
        self.fields["location"].required = target_code in {"IN_WAREHOUSE", "AT_DESTINATION"}
        self.fields["transport_reference"].required = target_code == "DISPATCHED"
        if target_code not in {"IN_WAREHOUSE", "AT_DESTINATION"}:
            self.fields.pop("location")
        if target_code != "DISPATCHED":
            self.fields.pop("transport_reference")


class PublicTrackingForm(forms.Form):
    order_number = forms.CharField(
        label="Número de orden",
        max_length=24,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej. CHI-2027-000001", "autocomplete": "off"}),
    )
    tracking_code = forms.RegexField(
        label="Código de seguimiento",
        regex=r"^\d{6}$",
        error_messages={"invalid": "Ingresa el código de seis dígitos."},
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "6 dígitos", "inputmode": "numeric", "maxlength": "6", "autocomplete": "off"}),
    )

    def clean_order_number(self):
        return self.cleaned_data["order_number"].strip().upper()
