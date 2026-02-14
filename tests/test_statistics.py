import os
import sqlite3
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

from app.analytics.statistics import StatsAnalyzer
from app.utils.logger import log


class StatsAnalyzerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._prev_log_disabled = log.disabled
        log.disabled = True

    @classmethod
    def tearDownClass(cls):
        log.disabled = cls._prev_log_disabled

    def setUp(self):
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp.close()
        self.db_path = temp.name

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE counts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    direction TEXT NOT NULL,
                    object_id INTEGER NOT NULL
                )
                """
            )

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except PermissionError:
                # No Windows, SQLite pode manter handle por mais tempo; não afeta determinismo do teste.
                pass

    def _insert_events(self, rows):
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                "INSERT INTO counts (timestamp, direction, object_id) VALUES (?, ?, ?)",
                rows,
            )

    def test_daily_report_uses_closed_open_range(self):
        self._insert_events(
            [
                ("2026-02-12 00:00:00", "IN", 1),   # include
                ("2026-02-12 23:59:59", "OUT", 2),  # include
                ("2026-02-13 00:00:00", "IN", 3),   # exclude (upper bound)
                ("2026-02-11 23:59:59", "OUT", 4),  # exclude (before lower bound)
            ]
        )

        analyzer = StatsAnalyzer(db_path=self.db_path)
        fixed_now = datetime(2026, 2, 12, 12, 0, 0)
        with patch("app.analytics.statistics.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_now
            report = analyzer.get_daily_report()

        self.assertEqual(report["IN"], 1)
        self.assertEqual(report["OUT"], 1)

    def test_hourly_peak_uses_closed_open_range(self):
        self._insert_events(
            [
                ("2026-02-12 08:10:00", "IN", 1),
                ("2026-02-12 08:20:00", "OUT", 2),
                ("2026-02-12 08:30:00", "IN", 3),
                ("2026-02-12 10:00:00", "IN", 4),
                ("2026-02-13 00:00:00", "IN", 5),  # exclude (upper bound)
            ]
        )

        analyzer = StatsAnalyzer(db_path=self.db_path)
        fixed_now = datetime(2026, 2, 12, 9, 0, 0)
        with patch("app.analytics.statistics.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_now
            peak = analyzer.get_hourly_peak()

        self.assertIsNotNone(peak)
        self.assertEqual(peak["hour"], "08")
        self.assertEqual(peak["count"], 3)


if __name__ == "__main__":
    unittest.main()
