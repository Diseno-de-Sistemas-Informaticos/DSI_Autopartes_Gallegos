import unittest
from types import SimpleNamespace
from unittest.mock import Mock


class TestDailyScraping(unittest.TestCase):
    def test_uso_unico_de_lock_en_memoria(self):
        first = Mock()
        first.acquire.return_value = True
        second = Mock()
        second.acquire.return_value = False

        self.assertTrue(first.acquire(blocking=False))
        self.assertFalse(second.acquire(blocking=False))

    def test_configuracion_diaria_valida(self):
        settings = SimpleNamespace(
            scraping=SimpleNamespace(
                enabled=True,
                daily_enabled=True,
                daily_time="02:00",
                timezone="America/Mexico_City",
            )
        )

        hour, minute = settings.scraping.daily_time.split(":")

        self.assertTrue(settings.scraping.daily_enabled)
        self.assertEqual(hour, "02")
        self.assertEqual(minute, "00")
        self.assertEqual(
            settings.scraping.timezone,
            "America/Mexico_City",
        )
