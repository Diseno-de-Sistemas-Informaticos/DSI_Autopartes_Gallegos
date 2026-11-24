import sys
from decimal import Decimal
from pathlib import Path
from threading import Lock
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api.dependencies import get_database_session
from app.core.config import get_settings
from app.repositories.scraping_repository import ScrapingRepository
from app.schemas.scraping import CompareRequest, ScrapingSearchRequest
from app.services.persistence_service import PersistenceService
from scraper.providers.sagaji_client import SagajiClient
from scraper.services.extraction import ejecutar_extraccion_sagaji


router = APIRouter(prefix="/api/scraping", tags=["scraping"])
_manual_lock = Lock()


def _to_bool(value):
    if value is None:
        return None
    return bool(value)


@router.post("/search")
def search_manual(
    payload: ScrapingSearchRequest,
    db: Session = Depends(get_database_session),
):
    if not _manual_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una búsqueda manual en proceso.",
        )

    repository = ScrapingRepository(db)
    term = payload.code if payload.search_type == "Codigo" else payload.description
    execution_id = repository.create_execution(term.strip(), payload.search_type)
    client = None

    try:
        settings = get_settings()
        if not settings.scraping.enabled:
            raise RuntimeError("El scraping está deshabilitado por configuración.")

        client = SagajiClient(
            max_retries=settings.scraping.max_retries,
            request_delay=settings.scraping.request_delay,
        )
        client.iniciar_sesion()

        extraction = ejecutar_extraccion_sagaji(
            client=client,
            termino=term.strip(),
            tipo_busqueda=payload.search_type,
            cuantos=settings.scraping.page_size,
            exportar_csv=False,
        )

        normalized = extraction["productos_normalizados"]
        original = extraction["resultado_original"]
        stats = PersistenceService(db).persist_capture(
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
            "pages": original["total_paginas"],
            "total_results": original["total_elementos_reportados"],
            "products": normalized,
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
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No fue posible completar la búsqueda.",
        ) from exc
    finally:
        if client is not None:
            client.session.close()
        _manual_lock.release()


@router.post("/daily/run")
def run_daily_manual(
    db: Session = Depends(get_database_session),
):
    settings = get_settings()
    if not settings.scraping.daily_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La extracción diaria está deshabilitada.",
        )

    try:
        from app.services.daily_scraping_service import DailyScrapingService

        result = DailyScrapingService(db, settings).run()
        return result
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get("/results")
def get_results(
    code: Optional[str] = None,
    description: Optional[str] = None,
    provider: Optional[str] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    availability: Optional[bool] = None,
    captured_from: Optional[str] = None,
    captured_to: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_database_session),
):
    offset = (page - 1) * page_size
    conditions = []
    parameters = {"offset": offset, "page_size": page_size}

    if code:
        conditions.append("pe.codigo_externo LIKE :code")
        parameters["code"] = f"%{code.strip()}%"
    if description:
        conditions.append(
            "(pe.descripcion_externa LIKE :description "
            "OR pe.nombre_externo LIKE :description)"
        )
        parameters["description"] = f"%{description.strip()}%"
    if provider:
        conditions.append("pr.nombre LIKE :provider")
        parameters["provider"] = f"%{provider.strip()}%"
    if min_price is not None:
        conditions.append("c.precio >= :min_price")
        parameters["min_price"] = min_price
    if max_price is not None:
        conditions.append("c.precio <= :max_price")
        parameters["max_price"] = max_price
    if availability is not None:
        conditions.append("c.disponible = :availability")
        parameters["availability"] = int(availability)
    if captured_from:
        conditions.append("c.fecha_captura >= :captured_from")
        parameters["captured_from"] = captured_from
    if captured_to:
        conditions.append("c.fecha_captura <= :captured_to")
        parameters["captured_to"] = captured_to

    where = " AND ".join(conditions)
    if where:
        where = "WHERE " + where

    query = text(
        f"""
        WITH capturas AS (
            SELECT hp.id_producto_externo,
                   hp.precio, hp.disponible,
                   hp.existencia_reportada, hp.fecha_captura,
                   ROW_NUMBER() OVER (
                       PARTITION BY hp.id_producto_externo
                       ORDER BY hp.fecha_captura DESC, hp.id_historial DESC
                   ) AS rn
            FROM Historial_precio hp
        )
        SELECT pe.id_producto_externo,
               pr.nombre AS proveedor,
               pe.sucursal_externa,
               pe.codigo_externo,
               pe.nombre_externo,
               pe.marca_externa,
               c.precio,
               c.disponible,
               c.existencia_reportada,
               c.fecha_captura,
               COUNT(*) OVER() AS total_count
        FROM capturas c
        JOIN Producto_externo pe
          ON pe.id_producto_externo = c.id_producto_externo
        LEFT JOIN Proveedor pr
          ON pr.id_proveedor = pe.id_proveedor
        WHERE c.rn = 1
        {(" AND " + " AND ".join(conditions)) if conditions else ""}
        ORDER BY c.fecha_captura DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY
        """
    )

    rows = db.execute(query, parameters).fetchall()
    total = int(rows[0].total_count) if rows else 0

    items = [
        {
            "id_external_product": row.id_producto_externo,
            "provider": row.proveedor,
            "branch": row.sucursal_externa,
            "code": row.codigo_externo,
            "name": row.nombre_externo,
            "brand": row.marca_externa,
            "price": row.precio,
            "availability": _to_bool(row.disponible),
            "stock": row.existencia_reportada,
            "captured_at": row.fecha_captura,
        }
        for row in rows
    ]

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/price-history/{id_producto_externo}")
def price_history(
    id_producto_externo: int,
    db: Session = Depends(get_database_session),
):
    rows = db.execute(
        text(
            """
            SELECT id_historial, precio, fecha_captura,
                   moneda, disponible, existencia_reportada,
                   id_ejecucion
            FROM Historial_precio
            WHERE id_producto_externo = :external_id
            ORDER BY fecha_captura ASC, id_historial ASC
            """
        ),
        {"external_id": id_producto_externo},
    ).fetchall()

    return {
        "id_external_product": id_producto_externo,
        "items": [
            {
                "id": row.id_historial,
                "price": row.precio,
                "captured_at": row.fecha_captura,
                "currency": row.moneda,
                "available": _to_bool(row.disponible),
                "stock": row.existencia_reportada,
                "execution_id": row.id_ejecucion,
            }
            for row in rows
        ],
    }


@router.get("/executions")
def executions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_database_session),
):
    offset = (page - 1) * page_size
    rows = db.execute(
        text(
            """
            SELECT id_ejecucion, termino_busqueda, tipo_busqueda,
                   fecha_inicio, fecha_fin, estado,
                   paginas_consultadas, total_resultados,
                   articulos_consultados, productos_nuevos,
                   precios_modificados, errores_encontrados,
                   mensaje_error,
                   COUNT(*) OVER() AS total_count
            FROM Ejecucion_scraping
            ORDER BY fecha_inicio DESC
            OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY
            """
        ),
        {"offset": offset, "page_size": page_size},
    ).fetchall()

    total = int(rows[0].total_count) if rows else 0
    return {
        "items": [
            {
                "id": row.id_ejecucion,
                "term": row.termino_busqueda,
                "search_type": row.tipo_busqueda,
                "started_at": row.fecha_inicio,
                "finished_at": row.fecha_fin,
                "status": row.estado,
                "pages": row.paginas_consultadas,
                "total_results": row.total_resultados,
                "articles": row.articulos_consultados,
                "new_products": row.productos_nuevos,
                "price_changes": row.precios_modificados,
                "errors": row.errores_encontrados,
                "error": row.mensaje_error,
            }
            for row in rows
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/executions/{id_ejecucion}")
def execution_detail(
    id_ejecucion: int,
    db: Session = Depends(get_database_session),
):
    row = db.execute(
        text(
            """
            SELECT id_ejecucion, id_usuario, termino_busqueda,
                   tipo_busqueda, fecha_inicio, fecha_fin,
                   estado, paginas_consultadas, total_resultados,
                   articulos_consultados, productos_nuevos,
                   precios_modificados, errores_encontrados,
                   mensaje_error
            FROM Ejecucion_scraping
            WHERE id_ejecucion = :execution_id
            """
        ),
        {"execution_id": id_ejecucion},
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada.")

    return {
        "id": row.id_ejecucion,
        "user_id": row.id_usuario,
        "term": row.termino_busqueda,
        "search_type": row.tipo_busqueda,
        "started_at": row.fecha_inicio,
        "finished_at": row.fecha_fin,
        "status": row.estado,
        "pages": row.paginas_consultadas,
        "total_results": row.total_resultados,
        "articles": row.articulos_consultados,
        "new_products": row.productos_nuevos,
        "price_changes": row.precios_modificados,
        "errors": row.errores_encontrados,
        "error": row.mensaje_error,
    }


@router.post("/compare")
def compare_products(
    payload: CompareRequest,
    db: Session = Depends(get_database_session),
):
    code = payload.code.strip()
    internal = db.execute(
        text(
            """
            SELECT TOP 1 id_producto
            FROM Producto
            WHERE codigo_fabricante = :code
               OR codigo_interno = :code
            """
        ),
        {"code": code},
    ).fetchone()

    rows = db.execute(
        text(
            """
            WITH latest AS (
                SELECT hp.*,
                       ROW_NUMBER() OVER (
                           PARTITION BY hp.id_producto_externo
                           ORDER BY hp.fecha_captura DESC, hp.id_historial DESC
                       ) AS rn
                FROM Historial_precio hp
            )
            SELECT pe.id_producto_externo,
                   pr.nombre AS proveedor,
                   pe.sucursal_externa,
                   pe.codigo_externo,
                   pe.nombre_externo,
                   pe.marca_externa,
                   hp.precio,
                   hp.disponible,
                   hp.existencia_reportada,
                   hp.fecha_captura
            FROM Producto_externo pe
            LEFT JOIN Proveedor pr
              ON pr.id_proveedor = pe.id_proveedor
            LEFT JOIN latest hp
              ON hp.id_producto_externo = pe.id_producto_externo
             AND hp.rn = 1
            WHERE pe.codigo_externo = :code
            ORDER BY hp.precio ASC
            """
        ),
        {"code": code},
    ).fetchall()

    items = [
        {
            "id_external_product": row.id_producto_externo,
            "provider": row.proveedor,
            "branch": row.sucursal_externa,
            "code": row.codigo_externo,
            "name": row.nombre_externo,
            "brand": row.marca_externa,
            "price": row.precio,
            "availability": _to_bool(row.disponible),
            "stock": row.existencia_reportada,
            "captured_at": row.fecha_captura,
            "equivalence_confirmed": bool(internal),
        }
        for row in rows
    ]

    if internal:
        lowest = min(
            (item for item in items if item["price"] is not None),
            key=lambda item: item["price"],
            default=None,
        )
        if lowest:
            lowest["lowest_confirmed_price"] = True

    return {
        "code": code,
        "internal_product_id": int(internal[0]) if internal else None,
        "equivalence_confirmed": bool(internal),
        "items": items,
    }
