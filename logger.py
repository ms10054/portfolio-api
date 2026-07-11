"""
Centralized logging system.
Logs to both console and rotating log files in the logs/ directory.

Log files:
  logs/app.log      — all INFO+ messages (general events)
  logs/errors.log   — ERROR+ only (exceptions, DB errors, server errors)
  logs/access.log   — every incoming HTTP request + response code
"""
import os
import logging
from logging.handlers import RotatingFileHandler


LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _make_handler(filename, level=logging.INFO):
    handler = RotatingFileHandler(
        os.path.join(LOG_DIR, filename),
        maxBytes=5 * 1024 * 1024,  # 5 MB per file
        backupCount=3,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    return handler


def setup_logging(app):
    """Attach file and console handlers to the Flask app logger."""
    app.logger.setLevel(logging.DEBUG if app.debug else logging.INFO)

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if app.debug else logging.INFO)
    console.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    # File handlers
    app_handler = _make_handler("app.log", logging.INFO)
    error_handler = _make_handler("errors.log", logging.ERROR)

    for handler in [console, app_handler, error_handler]:
        app.logger.addHandler(handler)

    # Also capture SQLAlchemy errors
    sql_logger = logging.getLogger("sqlalchemy.engine")
    sql_logger.addHandler(error_handler)

    app.logger.info("Logging system initialized")


def setup_access_log():
    """Return a logger for HTTP access events."""
    access_logger = logging.getLogger("access")
    access_logger.setLevel(logging.INFO)
    if not access_logger.handlers:
        access_logger.addHandler(_make_handler("access.log", logging.INFO))
    return access_logger
