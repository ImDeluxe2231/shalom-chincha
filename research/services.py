from decimal import Decimal
from statistics import mean, variance

from django.db.models import Avg, Count, Sum

from .models import (
    EfficiencySurvey,
    ResponseTimeObservation,
    StudyPhase,
    TraceabilityObservation,
)


def _as_float(value, digits=2):
    return round(float(value or 0), digits)


def _phase_traceability(phase):
    totals = TraceabilityObservation.objects.filter(phase=phase).aggregate(
        registered=Sum("total_registered"), tracked=Sum("correctly_tracked"), rows=Count("id")
    )
    registered = totals["registered"] or 0
    value = (totals["tracked"] or 0) * 100 / registered if registered else 0
    return {"value": round(value, 2), "rows": totals["rows"], "registered": registered, "tracked": totals["tracked"] or 0}


def _phase_response(phase):
    queryset = ResponseTimeObservation.objects.filter(phase=phase)
    overall = queryset.aggregate(value=Avg("duration_seconds"), rows=Count("id"))
    query = queryset.filter(operation=ResponseTimeObservation.Operation.QUERY).aggregate(value=Avg("duration_seconds"), rows=Count("id"))
    update = queryset.filter(operation=ResponseTimeObservation.Operation.UPDATE).aggregate(value=Avg("duration_seconds"), rows=Count("id"))
    return {
        "value": _as_float((overall["value"] or Decimal("0")) / Decimal("60")),
        "rows": overall["rows"],
        "query": _as_float((query["value"] or Decimal("0")) / Decimal("60")),
        "query_rows": query["rows"],
        "update": _as_float((update["value"] or Decimal("0")) / Decimal("60")),
        "update_rows": update["rows"],
    }


def _phase_efficiency(phase):
    surveys = list(EfficiencySurvey.objects.filter(phase=phase).select_related("participant"))
    if not surveys:
        return {"value": 0, "administrative": 0, "operational": 0, "rows": 0, "alpha": None}
    return {
        "value": round(mean(float(item.average_score) for item in surveys), 2),
        "administrative": round(mean(float(item.administrative_average) for item in surveys), 2),
        "operational": round(mean(float(item.operational_average) for item in surveys), 2),
        "rows": len(surveys),
        "alpha": cronbach_alpha(surveys),
    }


def cronbach_alpha(surveys):
    if len(surveys) < 2:
        return None
    answers = [item.answers for item in surveys]
    totals = [sum(row) for row in answers]
    if len(set(totals)) == 1:
        return None
    item_variances = []
    for index in range(10):
        values = [row[index] for row in answers]
        item_variances.append(variance(values) if len(set(values)) > 1 else 0)
    total_variance = variance(totals)
    if total_variance == 0:
        return None
    alpha = (10 / 9) * (1 - sum(item_variances) / total_variance)
    return round(alpha, 3)


def _improvement(pre, post, reverse=False):
    if not pre:
        return None
    change = ((pre - post) / pre * 100) if reverse else ((post - pre) / pre * 100)
    return round(change, 2)


def build_validation_summary():
    pre_trace = _phase_traceability(StudyPhase.PRETEST)
    post_trace = _phase_traceability(StudyPhase.POSTTEST)
    pre_response = _phase_response(StudyPhase.PRETEST)
    post_response = _phase_response(StudyPhase.POSTTEST)
    pre_efficiency = _phase_efficiency(StudyPhase.PRETEST)
    post_efficiency = _phase_efficiency(StudyPhase.POSTTEST)
    return {
        "traceability": {"pre": pre_trace, "post": post_trace, "improvement": _improvement(pre_trace["value"], post_trace["value"])},
        "response": {"pre": pre_response, "post": post_response, "improvement": _improvement(pre_response["value"], post_response["value"], reverse=True)},
        "efficiency": {"pre": pre_efficiency, "post": post_efficiency, "improvement": _improvement(pre_efficiency["value"], post_efficiency["value"])},
    }

