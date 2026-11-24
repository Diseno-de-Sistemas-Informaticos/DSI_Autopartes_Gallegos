from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import get_settings


settings = get_settings()

app = FastAPI(
    title="Autopartes Gallegos API",
    debug=settings.api.debug,
)

app.include_router(health_router)