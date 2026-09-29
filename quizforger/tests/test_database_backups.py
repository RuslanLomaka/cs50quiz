import sqlite3
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from quizforger.database_backups import backup_sqlite_database, sqlite_integrity_check


class DatabaseBackupTests(SimpleTestCase):
    def test_backup_is_complete_and_passes_integrity_check(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.sqlite3"
            connection = sqlite3.connect(source)
            connection.execute("CREATE TABLE sample (value TEXT NOT NULL)")
            connection.execute("INSERT INTO sample VALUES ('preserved')")
            connection.commit()
            connection.close()

            backup = backup_sqlite_database(source, root / "backups", keep=3)

            self.assertEqual(sqlite_integrity_check(backup), "ok")
            restored = sqlite3.connect(backup)
            try:
                self.assertEqual(
                    restored.execute("SELECT value FROM sample").fetchone()[0], "preserved"
                )
            finally:
                restored.close()

    def test_retention_keeps_only_requested_number(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.sqlite3"
            sqlite3.connect(source).close()

            for _ in range(4):
                backup_sqlite_database(source, root / "backups", keep=2)

            self.assertEqual(len(list((root / "backups").glob("quizforger-*.sqlite3"))), 2)
