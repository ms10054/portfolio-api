"""
Configuration — all sensitive values loaded from environment variables.
Copy .env.example to .env and fill in your values before running.
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env file automatically (ignored in production where env vars are set directly)
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


def _require_env(key, default=None):
    """Get an env var. In production (FLASK_ENV=production) it must be set."""
    value = os.environ.get(key, default)
    if value is None and os.environ.get("FLASK_ENV") == "production":
        raise RuntimeError(
            f"Required environment variable '{key}' is not set. "
            f"Please set it before running in production."
        )
    return value


class Config:
    # ── Security (MUST be set via env vars in production) ────────────────────
    SECRET_KEY = _require_env("SECRET_KEY", "dev-secret-key-change-in-production")
    JWT_SECRET_KEY = _require_env("JWT_SECRET_KEY", "dev-jwt-key-change-in-production")

    # ── Database ──────────────────────────────────────────────────────────────
    # Set DATABASE_URL=postgresql://user:pass@host:5432/dbname for PostgreSQL
    SQLALCHEMY_DATABASE_URI = _require_env(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(basedir, 'portfolio.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # ── JWT ───────────────────────────────────────────────────────────────────
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    # ── File Uploads ──────────────────────────────────────────────────────────
    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER", os.path.join(basedir, "uploads")
    )
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_MB", 5)) * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    IMAGE_MAX_DIMENSION = 1024

    # ── Pagination ────────────────────────────────────────────────────────────
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 50

    # ── Rate limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", 60))

    # ── Admin ─────────────────────────────────────────────────────────────────
    ADMIN_REGISTRATION_SECRET = _require_env("ADMIN_REGISTRATION_SECRET", "admin123")

    # ── Caching ───────────────────────────────────────────────────────────────
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 60

    # ── Environment ───────────────────────────────────────────────────────────
    ENV = os.environ.get("FLASK_ENV", "development")
    DEBUG = os.environ.get("FLASK_DEBUG", "1") == "1"


class ProductionConfig(Config):
    DEBUG = False
    CACHE_DEFAULT_TIMEOUT = 300   # longer cache in production


class DevelopmentConfig(Config):
    DEBUG = True


# Select config based on FLASK_ENV
config_map = {
    "production": ProductionConfig,
    "development": DevelopmentConfig,
}

def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    return config_map.get(env, DevelopmentConfig)
