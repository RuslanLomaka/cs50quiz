from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from quizforger.database_backups import backup_sqlite_database


class Command(BaseCommand):
    help = "Create an integrity-checked online backup of the configured SQLite database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--directory",
            default=None,
            help="Destination directory (defaults to QUIZFORGER_BACKUP_DIR or ./backups).",
        )
        parser.add_argument(
            "--keep", type=int, default=30, help="Number of newest backups to retain."
        )
        parser.add_argument(
            "--if-exists",
            action="store_true",
            help="Exit successfully when the database does not exist yet.",
        )

    def handle(self, *args, **options):
        database = settings.DATABASES["default"]
        if database["ENGINE"] != "django.db.backends.sqlite3":
            raise CommandError("backup_database currently supports SQLite only")

        source = Path(database["NAME"])
        if options["if_exists"] and not source.exists():
            self.stdout.write("Database does not exist yet; backup skipped.")
            return

        backup_dir = Path(options["directory"] or settings.QUIZFORGER_BACKUP_DIR)
        try:
            destination = backup_sqlite_database(source, backup_dir, keep=options["keep"])
        except (OSError, RuntimeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Verified backup: {destination}"))
