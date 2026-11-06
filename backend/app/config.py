"""Application configuration, driven by environment variables (12-factor)."""
import os
from urllib.parse import quote_plus


def _database_url():
    """Build the SQLAlchemy URL.

    Priority: DATABASE_URL, then POSTGRES_* variables (as injected by the
    Kubernetes ConfigMap + Secret), then a local SQLite file for development.
    """
    url = os.environ.get("DATABASE_URL")
    if url:
        return url

    host = os.environ.get("POSTGRES_HOST")
    if host:
        user = os.environ.get("POSTGRES_USER", "travel")
        password = quote_plus(os.environ.get("POSTGRES_PASSWORD", ""))
        port = os.environ.get("POSTGRES_PORT", "5432")
        name = os.environ.get("POSTGRES_DB", "travel")
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"

    return "sqlite:///travel-dev.db"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2 MB upload limit for JSON import
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    APP_VERSION = os.environ.get("APP_VERSION", "dev")
    METRICS_ENABLED = True

    # Enrichment (OpenStreetMap + Wikipedia). Disable it where there is no internet.
    ENRICHMENT_ENABLED = os.environ.get("ENRICHMENT_ENABLED", "true").lower() == "true"
    ENRICHMENT_TIMEOUT = float(os.environ.get("ENRICHMENT_TIMEOUT", "5"))
    GEOCODER_URL = os.environ.get("GEOCODER_URL", "https://nominatim.openstreetmap.org/search")
    WIKIPEDIA_URL = os.environ.get("WIKIPEDIA_URL", "https://en.wikipedia.org/api/rest_v1")
    HTTP_USER_AGENT = os.environ.get(
        "HTTP_USER_AGENT", "TravelLocationsApp/1.0 (student DevOps final project)"
    )
    SEED_FILE = os.environ.get(
        "SEED_FILE",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "seed", "locations.json"),
    )


class DevelopmentConfig(Config):
    DEBUG = True
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-not-secret")


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "testing"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    ENRICHMENT_ENABLED = False  # tests never call real external APIs


class ProductionConfig(Config):
    DEBUG = False


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name=None):
    name = name or os.environ.get("APP_ENV", "development")
    return CONFIGS.get(name, DevelopmentConfig)
