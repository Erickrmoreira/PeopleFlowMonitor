import os
import sqlite3
import tempfile
import unittest
from datetime import datetime

from app.services.counts_repository import CountsRepository


class CountsRepositoryTests(unittest.TestCase):
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
            conn.executemany(
                "INSERT INTO counts (timestamp, direction, object_id) VALUES (?, ?, ?)",
                [
                    ("2026-02-12 00:00:00", "IN", 1),
                    ("2026-02-12 12:00:00", "OUT", 2),
                    ("2026-02-13 00:00:00", "IN", 3),
                ],
            )

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except PermissionError:
                pass

    def test_fetch_counts_between_uses_closed_open_range(self):
        repo = CountsRepository(self.db_path)
        start_dt = datetime(2026, 2, 12, 0, 0, 0)
        end_dt = datetime(2026, 2, 13, 0, 0, 0)

        df = repo.fetch_counts_between(start_dt, end_dt)

        self.assertEqual(len(df), 2)
        self.assertListEqual(df["direction"].tolist(), ["IN", "OUT"])


if __name__ == "__main__":
    unittest.main()
