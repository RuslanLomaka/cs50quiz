import os
import sqlite3
import stat
import tempfile
from pathlib import Path
from unittest import skipIf

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

    def test_paths_with_uri_delimiters_are_encoded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source #1.sqlite3"
            sqlite3.connect(source).close()

            backup = backup_sqlite_database(source, root / "backups")

            self.assertEqual(sqlite_integrity_check(backup), "ok")

    def test_failed_backup_removes_partial_temporary_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "corrupt.sqlite3"
            source.write_bytes(b"not a sqlite database")
            backup_dir = root / "backups"

            with self.assertRaises(sqlite3.DatabaseError):
                backup_sqlite_database(source, backup_dir)

            self.assertEqual(list(backup_dir.glob("*.tmp")), [])
            self.assertEqual(list(backup_dir.glob("*.sqlite3")), [])

    @skipIf(os.name == "nt", "POSIX file modes are not available on Windows")
    def test_published_backup_is_owner_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.sqlite3"
            sqlite3.connect(source).close()

            backup = backup_sqlite_database(source, root / "backups")

            self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)
