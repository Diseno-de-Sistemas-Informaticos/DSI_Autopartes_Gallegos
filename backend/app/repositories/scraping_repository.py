from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


class ScrapingRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_execution(
        self,
        term: str,
        search_type: str,
        user_id: Optional[int] = None,
    ) -> int:
        row = self.db.execute(
            text(
                """
                INSERT INTO Ejecucion_scraping (
                    id_usuario, termino_busqueda, tipo_busqueda,
                    fecha_inicio, estado
                )
                OUTPUT INSERTED.id_ejecucion
                VALUES (:user_id, :term, :search_type, SYSDATETIME(), 'En proceso')
                """
            ),
            {
                "user_id": user_id,
                "term": term,
                "search_type": search_type,
            },
        ).fetchone()
        self.db.commit()
        return int(row[0])

    def finish_execution(
        self,
        execution_id: int,
        state: str,
        pages: int,
        total_results: int,
        articles: int,
        new_products: int,
        price_changes: int,
        errors: int,
        error_message: Optional[str] = None,
    ) -> None:
        self.db.execute(
            text(
                """
                UPDATE Ejecucion_scraping
                SET fecha_fin = SYSDATETIME(),
                    estado = :state,
                    paginas_consultadas = :pages,
                    total_resultados = :total_results,
                    articulos_consultados = :articles,
                    productos_nuevos = :new_products,
                    precios_modificados = :price_changes,
                    errores_encontrados = :errors,
                    mensaje_error = :error_message
                WHERE id_ejecucion = :execution_id
                """
            ),
            {
                "execution_id": execution_id,
                "state": state,
                "pages": pages,
                "total_results": total_results,
                "articles": articles,
                "new_products": new_products,
                "price_changes": price_changes,
                "errors": errors,
                "error_message": error_message,
            },
        )
        self.db.commit()

    def find_provider_by_name(self, name: str) -> Optional[int]:
        row = self.db.execute(
            text(
                """
                SELECT TOP 1 id_proveedor
                FROM Proveedor
                WHERE nombre = :name
                """
            ),
            {"name": name},
        ).fetchone()
        return int(row[0]) if row else None

    def create_provider(self, name: str) -> int:
        row = self.db.execute(
            text(
                """
                SELECT COALESCE(MAX(id_proveedor), 0) + 1
                FROM Proveedor
                """
            )
        ).fetchone()
        provider_id = int(row[0])
        self.db.execute(
            text(
                """
                INSERT INTO Proveedor (id_proveedor, nombre)
                VALUES (:provider_id, :name)
                """
            ),
            {"provider_id": provider_id, "name": name},
        )
        self.db.flush()
        return provider_id

    def find_external(
        self,
        provider_id: int,
        branch: str,
        external_code: str,
    ) -> Optional[int]:
        row = self.db.execute(
            text(
                """
                SELECT TOP 1 id_producto_externo
                FROM Producto_externo
                WHERE id_proveedor = :provider_id
                  AND COALESCE(sucursal_externa, '') = :branch
                  AND codigo_externo = :external_code
                """
            ),
            {
                "provider_id": provider_id,
                "branch": branch or "",
                "external_code": external_code,
            },
        ).fetchone()
        return int(row[0]) if row else None

    def create_external(
        self,
        provider_id: int,
        branch: str,
        external_code: str,
        name: str,
        description: str,
        brand: str,
    ) -> int:
        row = self.db.execute(
            text(
                """
                INSERT INTO Producto_externo (
                    id_producto, fuente_nombre, url_producto,
                    codigo_externo, nombre_externo, marca_externa,
                    id_proveedor, sucursal_externa, descripcion_externa
                )
                OUTPUT INSERTED.id_producto_externo
                VALUES (
                    NULL, 'SAGAJI', NULL,
                    :external_code, :name, :brand,
                    :provider_id, :branch, :description
                )
                """
            ),
            {
                "provider_id": provider_id,
                "branch": branch or "",
                "external_code": external_code,
                "name": name,
                "brand": brand,
                "description": description,
            },
        ).fetchone()
        return int(row[0])

    def update_external(
        self,
        external_id: int,
        name: str,
        description: str,
        brand: str,
    ) -> None:
        self.db.execute(
            text(
                """
                UPDATE Producto_externo
                SET nombre_externo = :name,
                    descripcion_externa = :description,
                    marca_externa = :brand
                WHERE id_producto_externo = :external_id
                """
            ),
            {
                "external_id": external_id,
                "name": name,
                "description": description,
                "brand": brand,
            },
        )

    def get_latest_price(
        self,
        external_id: int,
    ) -> Optional[tuple[Decimal, bool | None, int | None, datetime]]:
        row = self.db.execute(
            text(
                """
                SELECT TOP 1 precio, disponible,
                       existencia_reportada, fecha_captura
                FROM Historial_precio
                WHERE id_producto_externo = :external_id
                ORDER BY fecha_captura DESC, id_historial DESC
                """
            ),
            {"external_id": external_id},
        ).fetchone()
        if not row:
            return None
        return (
            Decimal(str(row[0])) if row[0] is not None else None,
            row[1],
            row[2],
            row[3],
        )

    def insert_history(
        self,
        external_id: int,
        execution_id: int,
        price: Optional[Decimal],
        available: Optional[bool],
        reported_stock: Optional[int],
        external_code: str,
    ) -> None:
        self.db.execute(
            text(
                """
                INSERT INTO Historial_precio (
                    id_producto_externo, precio, fecha_captura,
                    codigo_externo, id_ejecucion, moneda,
                    disponible, existencia_reportada
                )
                VALUES (
                    :external_id, :price, SYSDATETIME(),
                    :external_code, :execution_id, 'MXN',
                    :available, :reported_stock
                )
                """
            ),
            {
                "external_id": external_id,
                "price": price,
                "external_code": external_code,
                "execution_id": execution_id,
                "available": available,
                "reported_stock": reported_stock,
            },
        )
