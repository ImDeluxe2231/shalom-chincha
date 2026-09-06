from django import forms

from .models import (
    EfficiencySurvey,
    ResponseTimeObservation,
    StudyParticipant,
    TraceabilityObservation,
)


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                css_class = "form-select"
            else:
                css_class = "form-control"
            field.widget.attrs["class"] = f"{field.widget.attrs.get('class', '')} {css_class}".strip()


class TraceabilityObservationForm(StyledModelForm):
    class Meta:
        model = TraceabilityObservation
        fields = ("phase", "observed_on", "total_registered", "correctly_tracked", "notes")
        widgets = {"observed_on": forms.DateInput(attrs={"type": "date"})}


class ResponseTimeObservationForm(StyledModelForm):
    class Meta:
        model = ResponseTimeObservation
        fields = ("phase", "operation", "started_at", "finished_at", "notes")
        widgets = {
            "started_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "finished_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["started_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["finished_at"].input_formats = ["%Y-%m-%dT%H:%M"]


class EfficiencySurveyForm(StyledModelForm):
    participant_code = forms.RegexField(
        label="Código anónimo del participante",
        regex=r"(?i)^P(?:0[1-9]|1[0-5])$",
        max_length=3,
        error_messages={"invalid": "Utiliza un código entre P01 y P15."},
        help_text="Identifica al trabajador únicamente con un código entre P01 y P15.",
    )
    participant_area = forms.ChoiceField(
        label="Área del participante",
        choices=StudyParticipant.Area.choices,
    )

    class Meta:
        model = EfficiencySurvey
        fields = ("phase", "observed_on") + tuple(f"q{number}" for number in range(1, 11))
        widgets = {"observed_on": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(("participant_code", "participant_area", "phase", "observed_on") + tuple(f"q{number}" for number in range(1, 11)))
        for number in range(1, 11):
            self.fields[f"q{number}"].widget = forms.Select(
                choices=[("", "Seleccionar"), (1, "1 · Muy insatisfecho"), (2, "2 · Insatisfecho"), (3, "3 · Neutral"), (4, "4 · Satisfecho"), (5, "5 · Muy satisfecho")],
                attrs={"class": "form-select"},
            )

    def clean_participant_code(self):
        return self.cleaned_data["participant_code"].strip().upper()

    def clean(self):
        cleaned = super().clean()
        code = cleaned.get("participant_code")
        phase = cleaned.get("phase")
        if code and phase:
            participant = StudyParticipant.objects.filter(code=code).first()
            if participant and EfficiencySurvey.objects.filter(participant=participant, phase=phase).exists():
                raise forms.ValidationError(
                    f"El participante {code} ya tiene un cuestionario registrado para {dict(EfficiencySurvey._meta.get_field('phase').choices)[phase]}."
                )
        return cleaned
