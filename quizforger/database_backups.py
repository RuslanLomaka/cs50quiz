import logging
import os
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def sqlite_read_only_uri(database_path: Path) -> str:
    """Return an encoded absolute SQLite URI that cannot reinterpret path characters."""

    return f"{database_path.resolve().as_uri()}?mode=ro"


def sqlite_integrity_check(database_path: Path) -> str:
    with closing(sqlite3.connect(sqlite_read_only_uri(database_path), uri=True)) as connection:
        return str(connection.execute("PRAGMA integrity_check").fetchone()[0])


def backup_sqlite_database(database_path: Path, backup_dir: Path, *, keep: int = 30) -> Path:
    """Create and verify an online SQLite snapshot, then prune only older snapshots."""

    database_path = database_path.resolve()
    backup_dir = backup_dir.resolve()
    if not database_path.is_file():
        raise FileNotFoundError(database_path)
    if keep < 1:
        raise ValueError("keep must be at least 1")

    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = backup_dir / f"quizforger-{timestamp}.sqlite3"
    counter = 1
    while destination.exists():
        destination = backup_dir / f"quizforger-{timestamp}-{counter}.sqlite3"
        counter += 1
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{destination.stem}-",
            suffix=".tmp",
            dir=backup_dir,
            delete=False,
        ) as temporary_file:
            temporary = Path(temporary_file.name)
        temporary.chmod(0o600)

        with (
            closing(
                sqlite3.connect(sqlite_read_only_uri(database_path), uri=True, timeout=30)
            ) as source,
            closing(sqlite3.connect(temporary)) as target,
        ):
            source.backup(target)
            target.commit()
            integrity = str(target.execute("PRAGMA integrity_check").fetchone()[0])
            if integrity != "ok":
                raise RuntimeError(f"Backup integrity check failed: {integrity}")

        # Publish only after restrictive permissions and verification both succeed.
        temporary.chmod(0o600)
        os.replace(temporary, destination)
        temporary = None
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise

    backup_size = destination.stat().st_size
    snapshots = sorted(
        backup_dir.glob("quizforger-*.sqlite3"),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
        reverse=True,
    )
    for expired in snapshots[keep:]:
        expired.unlink()

    logger.info(
        "database_backup_completed",
        extra={
            "event": "database_backup_completed",
            "source": str(database_path),
            "destination": str(destination),
            "bytes": backup_size,
        },
    )
    return destination
