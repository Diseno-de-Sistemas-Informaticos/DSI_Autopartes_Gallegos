import unittest
from pathlib import Path


class TestFrontendContract(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        self.app_js = (root / "js" / "app.js").read_text(
            encoding="utf-8"
        )

    def test_scraping_module_has_no_local_storage_dependency(self):
        start = self.app_js.index("const SCRAPING_API_BASE")
        end = self.app_js.index("function navigate(key)")
        module = self.app_js[start:end]
        self.assertNotIn("localStorage", module)
        self.assertNotIn("sessionStorage", module)

    def test_scraping_module_uses_required_api_endpoints(self):
        start = self.app_js.index("const SCRAPING_API_BASE")
        end = self.app_js.index("function navigate(key)")
        module = self.app_js[start:end]

        for endpoint in (
            "/api/scraping/search",
            "/api/scraping/results",
            "/api/scraping/executions",
            "/api/scraping/daily/run",
            "/api/scraping/price-history/",
        ):
            self.assertIn(endpoint, module)

    def test_scraping_is_registered_in_navigation(self):
        self.assertIn("scraping:renderScraping", self.app_js)
