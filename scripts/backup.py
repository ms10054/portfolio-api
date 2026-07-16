"""Create a timestamped SQLite or PostgreSQL database backup."""
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]

BACKUP_DIR = ROOT / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

database_url = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{ROOT / 'portfolio.db'}"
)

timestamp = datetime.now(
    timezone.utc
).strftime("%Y%m%d_%H%M%S")

if database_url.startswith("sqlite:///"):
    source = Path(
        database_url.replace(
            "sqlite:///",
            "",
            1
        )
    )

    if not source.is_absolute():
        source = ROOT / source

    if not source.exists():
        raise SystemExit(
            f"Database not found: {source}"
        )

    target = (
        BACKUP_DIR
        / f"portfolio_{timestamp}.db"
    )

    shutil.copy2(source, target)

else:
    target = (
        BACKUP_DIR
        / f"portfolio_{timestamp}.sql"
    )

    parsed_url = urlparse(
        database_url.replace(
            "postgres://",
            "postgresql://",
            1
        )
    )

    environment = os.environ.copy()

    if parsed_url.password:
        environment["PGPASSWORD"] = (
            parsed_url.password
        )

    command = [
        "pg_dump",
        "--no-owner",
        "--no-privileges",
        "--file",
        str(target),
        database_url,
    ]

    subprocess.run(
        command,
        check=True,
        env=environment
    )

print(f"Backup created: {target}")