from fastapi import APIRouter

from app.core.database import test_database_connection


router = APIRouter(tags=["health"])


@router.get("/api/health")
def health():
    database_ok = False
    try:
        database_ok = test_database_connection()
    except Exception:
        database_ok = False

    return {
        "status": "ok" if database_ok else "degraded",
        "api": "ok",
        "database": "ok" if database_ok else "error",
    }