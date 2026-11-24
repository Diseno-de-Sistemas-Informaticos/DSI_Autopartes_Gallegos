from threading import Lock
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.repositories.scraping_repository import ScrapingRepository
from app.services.persistence_service import PersistenceService
from scraper.providers.sagaji_client import SagajiClient
from scraper.services.extraction import ejecutar_extraccion_sagaji


_daily_lock = Lock()


class DailyScrapingService:
    def __init__(
        self,
        db: Session,
        settings,
        client: Optional[SagajiClient] = None,
    ):
        self.db = db
        self.settings = settings
        self.client = client

    def acquire_database_lock(self) -> bool:
        row = self.db.execute(
            text(
                """
                DECLARE @result int;
                EXEC @result = sp_getapplock
                    @Resource = 'AutopartesGallegos_DailyScraping',
                    @LockMode = 'Exclusive',
                    @LockOwner = 'Session',
                    @LockTimeout = 0;
                SELECT @result;
                """
            )
        ).fetchone()
        return bool(row and int(row[0]) in (0, 1))

    def release_database_lock(self) -> None:
        self.db.execute(
            text(
                """
                EXEC sp_releaseapplock
                    @Resource = 'AutopartesGallegos_DailyScraping',
                    @LockOwner = 'Session';
                """
            )
        )
        self.db.commit()

    def run(self) -> dict:
        if not _daily_lock.acquire(blocking=False):
            raise RuntimeError("Ya existe una extracción diaria en proceso.")

        if not self.acquire_database_lock():
            _daily_lock.release()
            raise RuntimeError("Otra instancia ya está ejecutando la extracción diaria.")

        repository = ScrapingRepository(self.db)
        execution_id = repository.create_execution("", "General")
        client = self.client

        try:
            if not self.settings.scraping.enabled:
                raise RuntimeError("El scraping está deshabilitado por configuración.")
            if not self.settings.scraping.daily_enabled:
                raise RuntimeError("La extracción diaria está deshabilitada por configuración.")

            if client is None:
                client = SagajiClient(
                    max_retries=self.settings.scraping.max_retries,
                    request_delay=self.settings.scraping.request_delay,
                )

            client.iniciar_sesion()

            extraction = ejecutar_extraccion_sagaji(
                client=client,
                termino="",
                tipo_busqueda="Descripcion",
                cuantos=self.settings.scraping.page_size,
                exportar_csv=False,
            )

            original = extraction["resultado_original"]
            normalized = extraction["productos_normalizados"]
            stats = PersistenceService(self.db).persist_capture(
                execution_id,
                normalized,
            )

            repository.finish_execution(
                execution_id=execution_id,
                state="Completada",
                pages=int(original["total_paginas"]),
                total_results=int(original["total_elementos_reportados"]),
                articles=len(normalized),
                new_products=stats["new_products"],
                price_changes=stats["price_changes"],
                errors=0,
            )

            return {
                "execution_id": execution_id,
                "status": "Completada",
                "pages": int(original["total_paginas"]),
                "total_results": int(original["total_elementos_reportados"]),
                "comparison": stats,
            }

        except Exception as exc:
            repository.finish_execution(
                execution_id=execution_id,
                state="Error",
                pages=0,
                total_results=0,
                articles=0,
                new_products=0,
                price_changes=0,
                errors=1,
                error_message=str(exc),
            )
            raise
        finally:
            if client is not None and client.session is not None:
                client.session.close()
            self.release_database_lock()
            _daily_lock.release()
