from decimal import Decimal
import unittest
from unittest.mock import Mock, patch

from scraper.services.normalization import (
    normalizar_producto_sagaji,
    normalizar_productos_sagaji
)
from scraper.providers.sagaji_client import SagajiClient


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


class TestSagajiAdapter(unittest.TestCase):

    @patch.dict(
        "os.environ",
        {
            "SAGAJI_USER": "test-user",
            "SAGAJI_PASSWORD": "test-password",
        },
        clear=False
    )
    def test_paginacion_sin_limite_arbitrario(self):
        client = SagajiClient(
            max_retries=2,
            request_delay=0
        )
        client.autenticado = True
        client.filial = "01"
        client.canal = "01"
        client.login = "test-login"

        respuestas = [
            {
                "paginas": {
                    "totalPaginas": 3,
                    "totalElementos": 3
                },
                "productos": [{"filial": "01", "noparte": "A"}]
            },
            {
                "paginas": {},
                "productos": [{"filial": "01", "noparte": "B"}]
            },
            {
                "paginas": {},
                "productos": [{"filial": "01", "noparte": "C"}]
            }
        ]

        client.buscar_por_descripcion = Mock(
            side_effect=respuestas
        )

        resultado = client.buscar_todos_por_descripcion(
            "filtro",
            cuantos=10
        )

        self.assertEqual(resultado["total_paginas"], 3)
        self.assertEqual(resultado["total_productos_unicos"], 3)
        self.assertEqual(
            len(resultado["productos"]),
            3
        )

    @patch.dict(
        "os.environ",
        {
            "SAGAJI_USER": "test-user",
            "SAGAJI_PASSWORD": "test-password",
        },
        clear=False
    )
    def test_reintento_ante_error_temporal(self):
        client = SagajiClient(
            max_retries=2,
            request_delay=0
        )

        temporal = Mock(status_code=503)
        exitoso = Mock(status_code=200)
        client.session.get = Mock(
            side_effect=[temporal, exitoso]
        )

        respuesta = client._get_with_retries(
            client.BASE_URL,
            reauth=False
        )

        self.assertIs(respuesta, exitoso)
        self.assertEqual(client.session.get.call_count, 2)


if __name__ == "__main__":
    unittest.main()
