from datetime import timedelta
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

from .models import EfficiencySurvey, ResponseTimeObservation, StudyParticipant, StudyPhase, TraceabilityObservation
from .services import build_validation_summary


class ResearchModuleTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="thesis_admin", password="Prueba2027!", role=User.Role.ADMIN)
        self.operator = User.objects.create_user(username="thesis_operator", password="Prueba2027!", role=User.Role.OPERATIONAL)

    def test_only_administrator_can_open_validation_module(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("validation_dashboard")).status_code, 200)
        self.client.force_login(self.operator)
        self.assertEqual(self.client.get(reverse("validation_dashboard")).status_code, 403)

    def test_validation_contains_exactly_the_three_thesis_indicators(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("validation_dashboard"))
        for label in ("Indicador 01", "Indicador 02", "Indicador 03"):
            self.assertContains(response, label)
        self.assertNotContains(response, "Notificaciones automáticas")
        self.assertNotContains(response, "Métricas automáticas")
        for route_name in ("research_traceability_create", "research_response_time_create", "research_survey_create"):
            self.assertEqual(self.client.get(reverse(route_name)).status_code, 200, route_name)

    def test_traceability_post_saves_responsible_user(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("research_traceability_create"), {
            "phase": StudyPhase.PRETEST, "observed_on": "2026-08-30",
            "total_registered": 20, "correctly_tracked": 18, "notes": "Ficha 01",
        })
        self.assertRedirects(response, reverse("validation_dashboard"))
        observation = TraceabilityObservation.objects.get()
        self.assertEqual(observation.recorded_by, self.admin)
        self.assertEqual(observation.percentage, 90)

    def test_response_time_post_calculates_duration_and_user(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("research_response_time_create"), {
            "phase": StudyPhase.POSTTEST, "operation": ResponseTimeObservation.Operation.QUERY,
            "started_at": "2026-08-30T10:00", "finished_at": "2026-08-30T10:02",
            "notes": "Consulta controlada",
        })
        self.assertRedirects(response, reverse("validation_dashboard"))
        observation = ResponseTimeObservation.objects.get()
        self.assertEqual(observation.recorded_by, self.admin)
        self.assertEqual(float(observation.duration_seconds), 120)
        self.assertEqual(float(observation.duration_minutes), 2)

    def test_survey_post_creates_anonymous_participant_and_user(self):
        self.client.force_login(self.admin)
        data = {
            "participant_code": "p01", "participant_area": StudyParticipant.Area.ADMINISTRATIVE,
            "phase": StudyPhase.PRETEST, "observed_on": "2026-08-30",
        }
        data.update({f"q{number}": 4 for number in range(1, 11)})
        response = self.client.post(reverse("research_survey_create"), data)
        self.assertRedirects(response, reverse("validation_dashboard"))
        participant = StudyParticipant.objects.get(code="P01")
        survey = EfficiencySurvey.objects.get(participant=participant)
        self.assertEqual(participant.created_by, self.admin)
        self.assertEqual(survey.recorded_by, self.admin)
        self.assertEqual(survey.average_score, 4)

    def test_duplicate_survey_is_explained_without_server_error(self):
        participant = StudyParticipant.objects.create(code="P01", area=StudyParticipant.Area.OPERATIONAL, created_by=self.admin)
        EfficiencySurvey.objects.create(
            participant=participant, phase=StudyPhase.PRETEST, recorded_by=self.admin,
            **{f"q{number}": 3 for number in range(1, 11)},
        )
        self.client.force_login(self.admin)
        data = {
            "participant_code": "P01", "participant_area": StudyParticipant.Area.OPERATIONAL,
            "phase": StudyPhase.PRETEST, "observed_on": "2026-08-30",
        }
        data.update({f"q{number}": 5 for number in range(1, 11)})
        response = self.client.post(reverse("research_survey_create"), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ya tiene un cuestionario registrado")
        self.assertEqual(EfficiencySurvey.objects.count(), 1)

    def test_traceability_formula_and_phase_comparison(self):
        TraceabilityObservation.objects.create(phase=StudyPhase.PRETEST, total_registered=20, correctly_tracked=12, recorded_by=self.admin)
        TraceabilityObservation.objects.create(phase=StudyPhase.POSTTEST, total_registered=20, correctly_tracked=19, recorded_by=self.admin)
        summary = build_validation_summary()
        self.assertEqual(summary["traceability"]["pre"]["value"], 60.0)
        self.assertEqual(summary["traceability"]["post"]["value"], 95.0)
        self.assertEqual(summary["traceability"]["improvement"], 58.33)

    def test_traceability_rejects_impossible_value(self):
        item = TraceabilityObservation(phase=StudyPhase.PRETEST, total_registered=5, correctly_tracked=6, recorded_by=self.admin)
        with self.assertRaises(ValidationError):
            item.save()

    def test_response_time_rejects_invalid_order(self):
        started = timezone.now()
        item = ResponseTimeObservation(
            phase=StudyPhase.POSTTEST, operation=ResponseTimeObservation.Operation.UPDATE,
            started_at=started, finished_at=started - timedelta(seconds=1), recorded_by=self.admin,
        )
        with self.assertRaises(ValidationError):
            item.save()

    def test_export_contains_only_the_three_thesis_databases(self):
        TraceabilityObservation.objects.create(phase=StudyPhase.PRETEST, total_registered=10, correctly_tracked=7, recorded_by=self.admin)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("research_export"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
        with ZipFile(BytesIO(response.content)) as archive:
            self.assertEqual(set(archive.namelist()), {
                "01_trazabilidad.csv", "02_tiempos_respuesta.csv",
                "03_cuestionario_eficiencia.csv", "LEEME.txt",
            })
            self.assertIn("PRETEST", archive.read("01_trazabilidad.csv").decode("utf-8-sig"))

    def test_portable_backup_contains_database_and_manifest(self):
        with TemporaryDirectory() as directory:
            call_command("backup_sistema", output=directory)
            archives = list(Path(directory).glob("shalom_respaldo_*.zip"))
            self.assertEqual(len(archives), 1)
            with ZipFile(archives[0]) as archive:
                self.assertIn("datos.json", archive.namelist())
                self.assertIn("manifest.json", archive.namelist())
