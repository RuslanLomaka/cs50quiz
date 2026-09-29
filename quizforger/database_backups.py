import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def sqlite_integrity_check(database_path: Path) -> str:
    database_path = database_path.resolve()
    connection = sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True)
    try:
        return str(connection.execute("PRAGMA integrity_check").fetchone()[0])
    finally:
        connection.close()


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
    temporary = destination.with_suffix(".sqlite3.tmp")

    source = sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True, timeout=30)
    target = sqlite3.connect(temporary)
    try:
        source.backup(target)
        target.commit()
        integrity = str(target.execute("PRAGMA integrity_check").fetchone()[0])
        if integrity != "ok":
            raise RuntimeError(f"Backup integrity check failed: {integrity}")
    finally:
        target.close()
        source.close()

    os.replace(temporary, destination)
    try:
        destination.chmod(0o600)
    except OSError:
        logger.warning(
            "backup_permissions_not_changed",
            extra={"event": "backup_permissions_not_changed", "path": str(destination)},
        )

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
