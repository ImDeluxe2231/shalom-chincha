import csv
from io import BytesIO, StringIO
from zipfile import ZIP_DEFLATED, ZipFile

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render

from accounts.decorators import admin_role_required

from .forms import (
    EfficiencySurveyForm,
    ResponseTimeObservationForm,
    TraceabilityObservationForm,
)
from .models import (
    EfficiencySurvey,
    ResponseTimeObservation,
    StudyParticipant,
    TraceabilityObservation,
)
from .services import build_validation_summary


@admin_role_required
def validation_dashboard(request):
    return render(request, "research/dashboard.html", {
        "summary": build_validation_summary(),
        "traceability_records": TraceabilityObservation.objects.select_related("recorded_by")[:8],
        "response_records": ResponseTimeObservation.objects.select_related("recorded_by")[:8],
        "survey_records": EfficiencySurvey.objects.select_related("participant", "recorded_by").order_by("-created_at")[:8],
        "section": "validation",
    })


def _create_record(request, *, form_class, title, subtitle, success_message):
    form = form_class(request.POST or None)
    if request.method == "POST" and form.is_valid():
        instance = form.save(commit=False)
        model_fields = {field.name for field in instance._meta.fields}
        if "recorded_by" in model_fields:
            instance.recorded_by = request.user
        if "created_by" in model_fields:
            instance.created_by = request.user
        instance.save()
        messages.success(request, success_message)
        return redirect("validation_dashboard")
    return render(request, "research/form.html", {
        "form": form,
        "title": title,
        "subtitle": subtitle,
        "section": "validation",
    })


@admin_role_required
def traceability_create(request):
    return _create_record(
        request,
        form_class=TraceabilityObservationForm,
        title="Indicador 1 · Trazabilidad de los envíos",
        subtitle="Registra los datos de la ficha del Anexo 2. El porcentaje se calcula automáticamente.",
        success_message="Observación de trazabilidad registrada.",
    )


@admin_role_required
def response_time_create(request):
    return _create_record(
        request,
        form_class=ResponseTimeObservationForm,
        title="Indicador 2 · Tiempos de respuesta",
        subtitle="Registra la hora inicial y final. El sistema calcula la diferencia en segundos y minutos.",
        success_message="Observación de tiempo registrada.",
    )


@admin_role_required
def survey_create(request):
    form = EfficiencySurveyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            participant, created = StudyParticipant.objects.get_or_create(
                code=form.cleaned_data["participant_code"],
                defaults={
                    "area": form.cleaned_data["participant_area"],
                    "created_by": request.user,
                },
            )
            if not created and participant.area != form.cleaned_data["participant_area"]:
                form.add_error(
                    "participant_area",
                    f"El código {participant.code} ya está asociado al área {participant.get_area_display()}.",
                )
            else:
                survey = form.save(commit=False)
                survey.participant = participant
                survey.recorded_by = request.user
                survey.save()
                messages.success(request, f"Cuestionario de {participant.code} registrado correctamente.")
                return redirect("validation_dashboard")
    return render(request, "research/form.html", {
        "form": form,
        "title": "Indicador 3 · Eficiencia administrativa y operativa",
        "subtitle": "Registra las diez respuestas Likert. El participante se crea automáticamente con un código entre P01 y P15.",
        "section": "validation",
    })


def _csv_bytes(headers, rows):
    stream = StringIO(newline="")
    writer = csv.writer(stream, delimiter=";")
    writer.writerow(headers)
    writer.writerows(rows)
    return ("\ufeff" + stream.getvalue()).encode("utf-8")


@admin_role_required
def export_validation_data(request):
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        traceability = TraceabilityObservation.objects.select_related("recorded_by").order_by("observed_on", "id")
        archive.writestr("01_trazabilidad.csv", _csv_bytes(
            ["id", "fase", "fecha", "envios_registrados", "envios_rastreados", "porcentaje", "responsable"],
            ([item.pk, item.phase, item.observed_on.isoformat(), item.total_registered, item.correctly_tracked, item.percentage, item.recorded_by.username] for item in traceability),
        ))
        response_times = ResponseTimeObservation.objects.select_related("recorded_by").order_by("started_at", "id")
        archive.writestr("02_tiempos_respuesta.csv", _csv_bytes(
            ["id", "fase", "operacion", "inicio", "fin", "segundos", "minutos", "responsable"],
            ([item.pk, item.phase, item.operation, item.started_at.isoformat(), item.finished_at.isoformat(), item.duration_seconds, item.duration_minutes, item.recorded_by.username] for item in response_times),
        ))
        surveys = EfficiencySurvey.objects.select_related("participant", "recorded_by").order_by("phase", "participant__code")
        archive.writestr("03_cuestionario_eficiencia.csv", _csv_bytes(
            ["id", "participante", "area", "fase", "fecha"] + [f"p{number}" for number in range(1, 11)] + ["puntaje_total", "promedio", "responsable"],
            ([item.pk, item.participant.code, item.participant.area, item.phase, item.observed_on.isoformat(), *item.answers, item.total_score, item.average_score, item.recorded_by.username] for item in surveys),
        ))
        archive.writestr(
            "LEEME.txt",
            "Los tres archivos corresponden exactamente a los tres indicadores de la tesis.\n"
            "Importe cada CSV en SPSS usando UTF-8 y punto y coma como delimitador.\n"
            "No mezcle datos demostrativos con las observaciones reales del pretest y postest.\n",
        )
    response = HttpResponse(output.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="shalom_validacion_tesis.zip"'
    response["X-Content-Type-Options"] = "nosniff"
    return response
