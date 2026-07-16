"""Rotating application, error, and HTTP access logs."""
import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(
    os.path.dirname(__file__),
    "logs"
)

os.makedirs(LOG_DIR, exist_ok=True)

LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | "
    "%(name)s | %(message)s"
)

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _make_handler(filename, level=logging.INFO):
    handler = RotatingFileHandler(
        os.path.join(LOG_DIR, filename),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )

    handler.setLevel(level)

    handler.setFormatter(
        logging.Formatter(
            LOG_FORMAT,
            DATE_FORMAT
        )
    )

    return handler


def setup_logging(app):
    app.logger.handlers.clear()
    app.logger.propagate = False

    app.logger.setLevel(
        logging.DEBUG if app.debug else logging.INFO
    )

    console = logging.StreamHandler()

    console.setLevel(
        logging.DEBUG if app.debug else logging.INFO
    )

    console.setFormatter(
        logging.Formatter(
            LOG_FORMAT,
            DATE_FORMAT
        )
    )

    handlers = (
        console,
        _make_handler("app.log"),
        _make_handler(
            "errors.log",
            logging.ERROR
        ),
    )

    for handler in handlers:
        app.logger.addHandler(handler)

    logging.getLogger(
        "sqlalchemy.engine"
    ).addHandler(
        _make_handler(
            "errors.log",
            logging.ERROR
        )
    )

    app.logger.info("Logging system initialized")


def setup_access_log():
    logger = logging.getLogger(
        "portfolio.access"
    )

    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        logger.addHandler(
            _make_handler("access.log")
        )

    return logger