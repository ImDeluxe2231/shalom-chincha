from django.contrib import admin

from .models import EfficiencySurvey, ResponseTimeObservation, StudyParticipant, TraceabilityObservation


@admin.register(StudyParticipant)
class StudyParticipantAdmin(admin.ModelAdmin):
    list_display = ("code", "area", "is_active", "created_at")
    list_filter = ("area", "is_active")
    search_fields = ("code",)


@admin.register(TraceabilityObservation)
class TraceabilityObservationAdmin(admin.ModelAdmin):
    list_display = ("phase", "observed_on", "total_registered", "correctly_tracked", "percentage")
    list_filter = ("phase",)


@admin.register(ResponseTimeObservation)
class ResponseTimeObservationAdmin(admin.ModelAdmin):
    list_display = ("phase", "operation", "started_at", "duration_seconds")
    list_filter = ("phase", "operation")


@admin.register(EfficiencySurvey)
class EfficiencySurveyAdmin(admin.ModelAdmin):
    list_display = ("participant", "phase", "observed_on", "average_score")
    list_filter = ("phase", "participant__area")
