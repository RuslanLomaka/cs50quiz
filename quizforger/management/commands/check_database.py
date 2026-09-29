import sqlite3
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from quizforger.database_backups import sqlite_integrity_check, sqlite_read_only_uri


class Command(BaseCommand):
    help = "Run database integrity and application-data sanity checks without exposing user data."

    def handle(self, *args, **options):
        database = settings.DATABASES["default"]
        if database["ENGINE"] != "django.db.backends.sqlite3":
            self.stdout.write(
                self.style.WARNING("Only Django checks are available for this database backend.")
            )
            return

        database_path = Path(database["NAME"])
        if not database_path.is_file():
            raise CommandError(f"Database not found: {database_path}")
        integrity = sqlite_integrity_check(database_path)
        if integrity != "ok":
            raise CommandError(f"SQLite integrity check failed: {integrity}")

        connection = sqlite3.connect(sqlite_read_only_uri(database_path), uri=True)
        try:
            invalid_attempts = connection.execute(
                "SELECT COUNT(1) FROM quizforger_attempt "
                "WHERE total <= 0 OR score < 0 OR score > total"
            ).fetchone()[0]
            duplicate_email_groups = connection.execute(
                "SELECT COUNT(1) FROM ("
                "SELECT lower(email) FROM auth_user WHERE length(email) != 0 "
                "GROUP BY lower(email) HAVING COUNT(1) > 1"
                ")"
            ).fetchone()[0]
        finally:
            connection.close()

        if invalid_attempts:
            raise CommandError(f"Found {invalid_attempts} invalid attempt rows")
        self.stdout.write(self.style.SUCCESS("SQLite integrity: ok"))
        self.stdout.write("Invalid attempts: 0")
        if duplicate_email_groups:
            self.stdout.write(
                self.style.WARNING(
                    f"Duplicate case-insensitive email groups: {duplicate_email_groups}; clean these before enforcing uniqueness."
                )
            )
        else:
            self.stdout.write("Duplicate case-insensitive email groups: 0")
