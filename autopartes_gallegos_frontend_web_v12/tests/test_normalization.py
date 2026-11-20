from decimal import Decimal
import unittest

from scraper.services.normalization import (
    normalizar_producto_sagaji,
    normalizar_productos_sagaji
)


class TestNormalization(unittest.TestCase):

    def setUp(self):

        self.producto = {
            "filial": "01",
            "noparte": "FGI32",
            "descripcion": "FILTRO COMBUSTIBLE AFINACION INTERFIL",
            "descripcionlarga": "FILTRO DE COMBUSTIBLE",
            "descripcionlinea": "INTERFIL",
            "descripcionfamilia": "FILTROS",
            "descripcioncategoria": "COMBUSTIBLE",
            "unidadmedida": "PIEZA",
            "especificacion": "UNIVERSAL",
            "precio": "27.24",
            "existencia": "17",
            "multiploventa": "1"
        }

    def test_normalizar_producto(self):

        resultado = normalizar_producto_sagaji(self.producto)

        self.assertEqual(resultado["numero_parte"], "FGI32")
        self.assertEqual(resultado["marca"], "INTERFIL")
        self.assertEqual(resultado["precio"], Decimal("27.24"))
        self.assertEqual(resultado["existencia"], 17)

    def test_producto_sin_numero_parte(self):

        producto = self.producto.copy()
        producto["noparte"] = ""

        resultado = normalizar_productos_sagaji([producto])

        self.assertEqual(len(resultado), 0)

    def test_normalizar_lista(self):

        productos = [
            self.producto,
            self.producto.copy()
        ]

        resultado = normalizar_productos_sagaji(productos)

        self.assertEqual(len(resultado), 2)


if __name__ == "__main__":
    unittest.main()
