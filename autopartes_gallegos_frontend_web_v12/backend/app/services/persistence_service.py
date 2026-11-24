from sqlalchemy.orm import Session

from app.repositories.scraping_repository import ScrapingRepository
from app.services.comparison_service import compare_capture


class PersistenceService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ScrapingRepository(db)

    def persist_capture(
        self,
        execution_id: int,
        normalized_products: list[dict],
    ) -> dict:
        new_products = 0
        price_changes = 0
        availability_changes = 0
        stock_changes = 0

        provider_id = self.repository.find_provider_by_name("SAGAJI")
        if provider_id is None:
            provider_id = self.repository.create_provider("SAGAJI")

        try:
            for product in normalized_products:
                external_code = product["numero_parte"]
                branch = product.get("filial") or ""

                external_id = self.repository.find_external(
                    provider_id,
                    branch,
                    external_code,
                )

                if external_id is None:
                    external_id = self.repository.create_external(
                        provider_id=provider_id,
                        branch=branch,
                        external_code=external_code,
                        name=product.get("descripcion") or "",
                        description=product.get("descripcion_larga") or "",
                        brand=product.get("marca") or "",
                    )

                else:
                    self.repository.update_external(
                        external_id,
                        name=product.get("descripcion") or "",
                        description=product.get("descripcion_larga") or "",
                        brand=product.get("marca") or "",
                    )

                latest = self.repository.get_latest_price(external_id)
                comparison = compare_capture(product, latest)

                if comparison.is_new:
                    new_products += 1
                if comparison.price_changed:
                    price_changes += 1
                if comparison.availability_changed:
                    availability_changes += 1
                if comparison.stock_changed:
                    stock_changes += 1

                stock = product.get("existencia")
                available = bool(stock > 0) if stock is not None else None

                self.repository.insert_history(
                    external_id=external_id,
                    execution_id=execution_id,
                    price=product.get("precio"),
                    available=available,
                    reported_stock=stock,
                    external_code=external_code,
                )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        return {
            "new_products": new_products,
            "price_changes": price_changes,
            "availability_changes": availability_changes,
            "stock_changes": stock_changes,
        }
