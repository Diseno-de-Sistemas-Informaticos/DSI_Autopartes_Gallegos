import unittest
from decimal import Decimal

from backend.app.services.comparison_service import compare_capture


class TestComparison(unittest.TestCase):
    def test_detecta_precio_modificado(self):
        product = {
            "numero_parte": "ABC123",
            "precio": Decimal("150.50"),
            "existencia": 5,
        }

        result = compare_capture(
            product,
            (Decimal("140.00"), True, 5, None),
        )

        self.assertFalse(result.is_new)
        self.assertTrue(result.price_changed)
        self.assertFalse(result.availability_changed)
        self.assertFalse(result.stock_changed)

    def test_detecta_producto_nuevo(self):
        result = compare_capture(
            {
                "numero_parte": "NEW001",
                "precio": Decimal("99.00"),
                "existencia": 2,
            },
            None,
        )

        self.assertTrue(result.is_new)
        self.assertFalse(result.price_changed)

    def test_existencia_reportada_cero_cambia_disponibilidad(self):
        result = compare_capture(
            {
                "numero_parte": "ABC123",
                "precio": Decimal("150.50"),
                "existencia": 0,
            },
            (Decimal("150.50"), True, 5, None),
        )

        self.assertTrue(result.availability_changed)
        self.assertTrue(result.stock_changed)
