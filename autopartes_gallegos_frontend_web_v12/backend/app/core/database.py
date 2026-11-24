from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


settings = get_settings()


def build_database_url() -> URL:
    sql = settings.sqlserver
    return URL.create(
        "mssql+pyodbc",
        username=sql.username,
        password=sql.password,
        host=sql.host,
        port=sql.port,
        database=sql.database,
        query={
            "driver": sql.driver,
            "Encrypt": "yes",
            "TrustServerCertificate": "yes",
        },
    )


def create_database_engine() -> Engine:
    return create_engine(
        build_database_url(),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


engine = create_database_engine()
SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    expire_on_commit=False,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_database_connection() -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True