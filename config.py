"""Environment-based configuration for the Portfolio Management API."""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()
BASEDIR = os.path.abspath(os.path.dirname(__file__))


def _require_env(key, default=None):
    value = os.environ.get(key, default)
    if value is None and os.environ.get("FLASK_ENV") == "production":
        raise RuntimeError(f"Required environment variable '{key}' is not set")
    return value


def _database_url():
    url = _require_env(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASEDIR, 'portfolio.db')}"
    )

    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return url


class Config:
    SECRET_KEY = _require_env(
        "SECRET_KEY",
        "dev-secret-key-change-in-production"
    )

    JWT_SECRET_KEY = _require_env(
        "JWT_SECRET_KEY",
        "dev-jwt-key-change-in-production"
    )

    ADMIN_REGISTRATION_SECRET = _require_env(
        "ADMIN_REGISTRATION_SECRET",
        "admin123"
    )

    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": int(os.environ.get("DB_POOL_SIZE", 5)),
        "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", 10)),
    }

    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=int(os.environ.get("JWT_EXPIRES_HOURS", 24))
    )

    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER",
        os.path.join(BASEDIR, "uploads")
    )

    MAX_CONTENT_LENGTH = (
        int(os.environ.get("MAX_CONTENT_MB", 5)) * 1024 * 1024
    )

    ALLOWED_IMAGE_EXTENSIONS = {
        "png",
        "jpg",
        "jpeg",
        "gif",
        "webp",
    }

    IMAGE_MAX_DIMENSION = 1024
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 50

    RATE_LIMIT_PER_MINUTE = int(
        os.environ.get("RATE_LIMIT_PER_MINUTE", 60)
    )

    CACHE_TYPE = os.environ.get(
        "CACHE_TYPE",
        "SimpleCache"
    )

    CACHE_DEFAULT_TIMEOUT = int(
        os.environ.get("CACHE_DEFAULT_TIMEOUT", 60)
    )

    ENV = os.environ.get("FLASK_ENV", "development")
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    JSON_SORT_KEYS = False
    PROPAGATE_EXCEPTIONS = False


class ProductionConfig(Config):
    DEBUG = False
    CACHE_DEFAULT_TIMEOUT = 300


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=30)
    RATE_LIMIT_PER_MINUTE = 1000
    CACHE_TYPE = "NullCache"


config_map = {
    "production": ProductionConfig,
    "development": DevelopmentConfig,
    "testing": TestingConfig,
}


def get_config():
    environment = os.environ.get(
        "FLASK_ENV",
        "development"
    )

    return config_map.get(
        environment,
        DevelopmentConfig
    )