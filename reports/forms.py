from datetime import timedelta

from django import forms
from django.utils import timezone

from shipments.models import Agency, Shipment


class ReportFilterForm(forms.Form):
    date_from = forms.DateField(
        label="Desde",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    date_to = forms.DateField(
        label="Hasta",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    agency = forms.ModelChoiceField(
        label="Agencia",
        queryset=Agency.objects.none(),
        required=False,
        empty_label="Todas las agencias",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    transport_mode = forms.ChoiceField(
        label="Transporte",
        choices=[("", "Todas las modalidades"), *Shipment.TransportMode.choices],
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["agency"].queryset = Agency.objects.order_by("name")

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("date_from")
        end = cleaned.get("date_to")
        if start and end:
            if start > end:
                self.add_error("date_to", "La fecha final no puede ser anterior a la inicial.")
            elif (end - start).days > 366:
                self.add_error("date_to", "Selecciona un periodo máximo de 366 días.")
        return cleaned


def bound_report_filter(data=None):
    today = timezone.localdate()
    defaults = {
        "date_from": (today - timedelta(days=29)).isoformat(),
        "date_to": today.isoformat(),
        "agency": "",
        "transport_mode": "",
    }
    return ReportFilterForm(data if data else defaults)
