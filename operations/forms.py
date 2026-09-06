import re

from django import forms
from django.core.exceptions import ValidationError

from accounts.models import User
from shipments.models import Shipment

from .models import Delivery, Incident


def validate_public_message(value):
    if re.search(r"\b\d{8,12}\b", value or "") or re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", value or ""):
        raise ValidationError("El mensaje público no debe incluir documentos, teléfonos ni correos electrónicos.")


class StyledModelForm(forms.ModelForm):
    def apply_styles(self):
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"


class DeliveryForm(StyledModelForm):
    tracking_code_confirmation = forms.RegexField(
        label="Código de seguimiento",
        regex=r"^\d{6}$",
        error_messages={"invalid": "Ingresa el código de seis dígitos."},
        widget=forms.TextInput(attrs={"class": "form-control", "inputmode": "numeric", "maxlength": "6", "autocomplete": "off", "placeholder": "6 dígitos"}),
    )
    confirm_payment = forms.BooleanField(
        label="Confirmo que el pago fue recibido",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    acceptance = forms.BooleanField(
        label="Confirmo la identidad del receptor y la entrega física de todos los bultos",
        required=True,
        error_messages={"required": "Debes confirmar la validación y entrega de los bultos."},
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = Delivery
        fields = (
            "delivery_method", "receiver_type", "receiver_name", "receiver_document_type",
            "receiver_document_number", "receiver_phone", "relationship", "verification_method",
            "package_condition", "condition_notes", "notes",
        )
        widgets = {
            "condition_notes": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, shipment, **kwargs):
        super().__init__(*args, **kwargs)
        self.shipment = shipment
        self.apply_styles()
        self.fields["confirm_payment"].required = shipment.payment_status != Shipment.PaymentStatus.PAID
        if shipment.payment_status == Shipment.PaymentStatus.PAID:
            self.fields["confirm_payment"].initial = True
            self.fields["confirm_payment"].disabled = True
        recipient = shipment.recipient
        if not self.is_bound:
            self.initial["delivery_method"] = Delivery.DeliveryMethod.ADDRESS if shipment.service_type == Shipment.ServiceType.ADDRESS else Delivery.DeliveryMethod.AGENCY
            self.initial["receiver_type"] = Delivery.ReceiverType.RECIPIENT if recipient.customer_type == "PERSON" else Delivery.ReceiverType.AUTHORIZED
            if recipient.customer_type == "PERSON":
                self.initial["receiver_name"] = recipient.display_name
                self.initial["receiver_document_type"] = recipient.document_type
                self.initial["receiver_document_number"] = recipient.document_number
                self.initial["receiver_phone"] = recipient.phone
            self.initial["verification_method"] = (
                Delivery.VerificationMethod.DOCUMENT_CODE
                if recipient.customer_type == "PERSON"
                else Delivery.VerificationMethod.AUTHORIZATION
            )
            self.initial["package_condition"] = Delivery.PackageCondition.CONFORMING

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("tracking_code_confirmation") != self.shipment.tracking_code:
            self.add_error("tracking_code_confirmation", "El código no coincide con este envío.")
        expected_method = Delivery.DeliveryMethod.ADDRESS if self.shipment.service_type == Shipment.ServiceType.ADDRESS else Delivery.DeliveryMethod.AGENCY
        if cleaned.get("delivery_method") != expected_method:
            self.add_error("delivery_method", "La modalidad debe coincidir con el servicio contratado.")
        recipient = self.shipment.recipient
        if cleaned.get("receiver_type") == Delivery.ReceiverType.RECIPIENT:
            if recipient.customer_type != "PERSON":
                self.add_error("receiver_type", "Una empresa debe recibir mediante una persona autorizada.")
            elif cleaned.get("receiver_document_number", "").strip().upper() != recipient.document_number:
                self.add_error("receiver_document_number", "El documento no coincide con el destinatario registrado.")
        elif cleaned.get("receiver_type") == Delivery.ReceiverType.AUTHORIZED and cleaned.get("verification_method") != Delivery.VerificationMethod.AUTHORIZATION:
            self.add_error("verification_method", "Una persona autorizada requiere verificar documento, código y autorización.")
        if self.shipment.payment_status != Shipment.PaymentStatus.PAID and not cleaned.get("confirm_payment"):
            self.add_error("confirm_payment", "Confirma el pago antes de completar la entrega.")
        return cleaned


class IncidentForm(StyledModelForm):
    class Meta:
        model = Incident
        fields = ("agency", "incident_type", "severity", "description", "public_message", "evidence")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5, "placeholder": "Describe qué ocurrió, los bultos afectados y las acciones inmediatas"}),
            "public_message": forms.Textarea(attrs={"rows": 3, "placeholder": "Mensaje breve y prudente para la consulta pública"}),
            "evidence": forms.ClearableFileInput(attrs={"accept": ".jpg,.jpeg,.png,.pdf"}),
        }

    def __init__(self, *args, shipment, **kwargs):
        super().__init__(*args, **kwargs)
        self.shipment = shipment
        self.apply_styles()
        allowed_ids = {shipment.origin_id, shipment.destination_id}
        if shipment.current_agency_id:
            allowed_ids.add(shipment.current_agency_id)
        self.fields["agency"].queryset = self.fields["agency"].queryset.filter(pk__in=allowed_ids)
        if not self.is_bound:
            self.initial["agency"] = shipment.current_agency or shipment.origin
            self.initial["severity"] = Incident.Severity.MEDIUM

    def clean_public_message(self):
        value = self.cleaned_data.get("public_message", "").strip()
        validate_public_message(value)
        return value


class IncidentReviewForm(forms.Form):
    assigned_to = forms.ModelChoiceField(
        label="Responsable asignado",
        queryset=User.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    public_message = forms.CharField(
        label="Mensaje actualizado para el cliente",
        max_length=300,
        required=False,
        validators=[validate_public_message],
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = User.objects.filter(is_active=True).order_by("first_name", "last_name", "username")


class IncidentResolutionForm(forms.Form):
    resolution = forms.CharField(
        label="Solución aplicada",
        min_length=10,
        max_length=1000,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 5, "placeholder": "Describe la verificación realizada y la solución aplicada"}),
    )
    public_message = forms.CharField(
        label="Mensaje final para el cliente",
        max_length=300,
        required=False,
        validators=[validate_public_message],
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Ej. La incidencia fue atendida y el envío continúa su recorrido."}),
    )
    resume_confirmation = forms.BooleanField(
        label="Confirmo que el envío puede retomar su estado anterior",
        required=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
