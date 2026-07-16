"""Restore a backup. Usage: python scripts/restore.py backups/file.db-or-sql"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if len(sys.argv) != 2:
    raise SystemExit(
        "Usage: python scripts/restore.py <backup-file>"
    )

backup = Path(sys.argv[1]).resolve()

if not backup.exists():
    raise SystemExit(
        f"Backup not found: {backup}"
    )

database_url = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{ROOT / 'portfolio.db'}"
)

if database_url.startswith("sqlite:///"):
    target = Path(
        database_url.replace(
            "sqlite:///",
            "",
            1
        )
    )

    if not target.is_absolute():
        target = ROOT / target

    target.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    shutil.copy2(
        backup,
        target
    )

else:
    subprocess.run(
        [
            "psql",
            database_url,
            "--file",
            str(backup)
        ],
        check=True
    )

print("Database restored successfully")