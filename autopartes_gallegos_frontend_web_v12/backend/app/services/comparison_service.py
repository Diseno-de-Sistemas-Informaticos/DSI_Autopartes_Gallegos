from decimal import Decimal
from typing import Iterable, Optional


class ComparisonResult:
    def __init__(
        self,
        product: dict,
        is_new: bool,
        price_changed: bool,
        availability_changed: bool,
        stock_changed: bool,
        previous_price: Optional[Decimal],
    ):
        self.product = product
        self.is_new = is_new
        self.price_changed = price_changed
        self.availability_changed = availability_changed
        self.stock_changed = stock_changed
        self.previous_price = previous_price


def compare_capture(
    normalized_product: dict,
    latest: Optional[tuple],
) -> ComparisonResult:
    price = normalized_product.get("precio")
    stock = normalized_product.get("existencia")
    availability = bool(stock > 0) if stock is not None else None

    if latest is None:
        return ComparisonResult(
            normalized_product,
            is_new=True,
            price_changed=False,
            availability_changed=False,
            stock_changed=False,
            previous_price=None,
        )

    previous_price = latest[0]
    previous_availability = latest[1]
    previous_stock = latest[2]

    return ComparisonResult(
        normalized_product,
        is_new=False,
        price_changed=(
            price is not None
            and previous_price is not None
            and Decimal(price) != Decimal(previous_price)
        ),
        availability_changed=(
            availability is not None
            and previous_availability is not None
            and availability != bool(previous_availability)
        ),
        stock_changed=(
            stock is not None
            and previous_stock is not None
            and stock != previous_stock
        ),
        previous_price=previous_price,
    )


def find_confirmed_internal_match(db, external_code: str) -> Optional[int]:
    from sqlalchemy import text

    row = db.execute(
        text(
            """
            SELECT TOP 1 id_producto
            FROM Producto
            WHERE codigo_fabricante = :code
               OR codigo_interno = :code
            ORDER BY id_producto
            """
        ),
        {"code": external_code},
    ).fetchone()
    return int(row[0]) if row else None
