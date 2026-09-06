import json
from io import StringIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from django.conf import settings
from django.core.management import BaseCommand, call_command
from django.utils import timezone


class Command(BaseCommand):
    help = "Crea un respaldo portable de la base de datos y la carpeta media."

    def add_arguments(self, parser):
        parser.add_argument("--output", help="Directorio donde se guardará el respaldo.")

    def handle(self, *args, **options):
        output_dir = Path(options["output"] or (settings.BASE_DIR / "backups")).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = timezone.localtime().strftime("%Y%m%d_%H%M%S")
        archive_path = output_dir / f"shalom_respaldo_{timestamp}.zip"

        data_stream = StringIO()
        call_command(
            "dumpdata",
            exclude=["contenttypes", "auth.permission", "sessions"],
            indent=2,
            stdout=data_stream,
        )
        manifest = {
            "created_at": timezone.now().isoformat(),
            "database_engine": settings.DATABASES["default"]["ENGINE"],
            "format": "Django JSON + archivos media",
            "restore_command": "python manage.py loaddata datos.json",
        }
        with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
            archive.writestr("datos.json", data_stream.getvalue().encode("utf-8"))
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))
            media_root = Path(settings.MEDIA_ROOT)
            if media_root.exists():
                for file_path in media_root.rglob("*"):
                    if file_path.is_file():
                        archive.write(file_path, Path("media") / file_path.relative_to(media_root))

        self.stdout.write(self.style.SUCCESS(f"Respaldo creado: {archive_path}"))

