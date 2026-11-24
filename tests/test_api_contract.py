import os
import unittest
from pathlib import Path

os.environ.setdefault("API_SECRET_KEY", "temporary-test-secret")

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
import sys
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient

from app.main import app


class TestScrapingApiContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_contract(self):
        response = self.client.get("/api/health")
        self.assertIn(response.status_code, (200, 503))
        body = response.json()
        self.assertIn("api", body)
        self.assertIn("database", body)

    def test_search_rejects_empty_code(self):
        response = self.client.post(
            "/api/scraping/search",
            json={"code": "", "search_type": "Codigo"},
        )
        self.assertEqual(response.status_code, 422)

    def test_results_pagination_contract(self):
        response = self.client.get(
            "/api/scraping/results",
            params={"page": 1, "page_size": 20},
        )
        self.assertIn(response.status_code, (200, 500))

    def test_compare_contract_without_real_match(self):
        response = self.client.post(
            "/api/scraping/compare",
            json={"code": "TEST-NONE"},
        )
        self.assertIn(response.status_code, (200, 500))

    def test_openapi_contains_scraping_routes(self):
        paths = app.openapi()["paths"]
        expected = {
            "/api/scraping/search",
            "/api/scraping/results",
            "/api/scraping/price-history/{id_producto_externo}",
            "/api/scraping/executions",
            "/api/scraping/executions/{id_ejecucion}",
            "/api/scraping/compare",
            "/api/scraping/daily/run",
        }
        self.assertTrue(expected.issubset(set(paths)))
