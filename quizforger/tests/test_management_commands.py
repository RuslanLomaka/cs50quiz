import io
import sqlite3
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings


class DatabaseCommandTests(SimpleTestCase):
    def database_settings(self, path: Path) -> dict:
        return {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": path}}

    def test_backup_command_creates_verified_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.sqlite3"
            connection = sqlite3.connect(source)
            connection.execute("CREATE TABLE sample (value TEXT)")
            connection.close()
            output = io.StringIO()

            with override_settings(
                DATABASES=self.database_settings(source),
                QUIZFORGER_BACKUP_DIR=root / "backups",
            ):
                call_command("backup_database", keep=2, stdout=output)

            self.assertIn("Verified backup", output.getvalue())
            self.assertEqual(len(list((root / "backups").glob("*.sqlite3"))), 1)

    def test_backup_command_can_skip_missing_database(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = io.StringIO()
            with override_settings(
                DATABASES=self.database_settings(root / "missing.sqlite3"),
                QUIZFORGER_BACKUP_DIR=root / "backups",
            ):
                call_command("backup_database", if_exists=True, stdout=output)

            self.assertIn("backup skipped", output.getvalue())

    def test_backup_command_rejects_invalid_retention(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.sqlite3"
            sqlite3.connect(source).close()
            with override_settings(
                DATABASES=self.database_settings(source),
                QUIZFORGER_BACKUP_DIR=root / "backups",
            ):
                with self.assertRaises(CommandError):
                    call_command("backup_database", keep=0)

    def test_check_database_reports_integrity_and_duplicate_group(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.sqlite3"
            connection = sqlite3.connect(source)
            connection.execute("CREATE TABLE quizforger_attempt (score INTEGER, total INTEGER)")
            connection.execute("CREATE TABLE auth_user (email TEXT)")
            connection.executemany(
                "INSERT INTO auth_user VALUES (?)",
                [("same@example.com",), ("SAME@example.com",)],
            )
            connection.commit()
            connection.close()
            output = io.StringIO()

            with override_settings(DATABASES=self.database_settings(source)):
                call_command("check_database", stdout=output)

            self.assertIn("SQLite integrity: ok", output.getvalue())
            self.assertIn("Duplicate case-insensitive email groups: 1", output.getvalue())
