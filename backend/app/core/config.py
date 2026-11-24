import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Falta la variable obligatoria {name}. "
            "Copia .env.example a .env y configura sus valores."
        )
    return value


def _boolean(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _integer(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} debe ser un entero.") from exc


def _float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} debe ser un numero decimal.") from exc


@dataclass(frozen=True)
class SQLServerSettings:
    host: str
    port: int
    database: str
    username: str
    password: str
    driver: str


@dataclass(frozen=True)
class APISettings:
    host: str
    port: int
    debug: bool
    secret_key: str


@dataclass(frozen=True)
class SagajiSettings:
    user: str
    password: str
    remember: str


@dataclass(frozen=True)
class ScrapingSettings:
    enabled: bool
    daily_enabled: bool
    daily_time: str
    timezone: str
    request_delay: float
    max_retries: int
    page_size: int


@dataclass(frozen=True)
class Settings:
    sqlserver: SQLServerSettings
    api: APISettings
    sagaji: SagajiSettings
    scraping: ScrapingSettings


def get_settings() -> Settings:
    secret_key = os.getenv("API_SECRET_KEY", "").strip()
    if not secret_key:
        raise RuntimeError(
            "Falta la variable obligatoria API_SECRET_KEY. "
            "Copia .env.example a .env y configura sus valores."
        )

    return Settings(
        sqlserver=SQLServerSettings(
            host=_required("SQLSERVER_HOST"),
            port=_integer("SQLSERVER_PORT", 1433),
            database=_required("SQLSERVER_DATABASE"),
            username=_required("SQLSERVER_USERNAME"),
            password=_required("SQLSERVER_PASSWORD"),
            driver=_required("SQLSERVER_DRIVER"),
        ),
        api=APISettings(
            host=os.getenv("API_HOST", "127.0.0.1"),
            port=_integer("API_PORT", 8000),
            debug=_boolean("API_DEBUG", False),
            secret_key=secret_key,
        ),
        sagaji=SagajiSettings(
            user=_required("SAGAJI_USER"),
            password=_required("SAGAJI_PASSWORD"),
            remember=os.getenv("SAGAJI_REMEMBER", "0"),
        ),
        scraping=ScrapingSettings(
            enabled=_boolean("SCRAPING_ENABLED", True),
            daily_enabled=_boolean("SCRAPING_DAILY_ENABLED", True),
            daily_time=os.getenv("SCRAPING_DAILY_TIME", "02:00"),
            timezone=os.getenv("SCRAPING_TIMEZONE", "America/Mexico_City"),
            request_delay=_float("SCRAPING_REQUEST_DELAY", 1.0),
            max_retries=_integer("SCRAPING_MAX_RETRIES", 3),
            page_size=_integer("SCRAPING_PAGE_SIZE", 10),
        ),
    )