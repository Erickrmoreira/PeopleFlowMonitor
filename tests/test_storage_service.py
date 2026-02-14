import os
import sqlite3
import tempfile
import unittest

from app.services.storage import StorageService
from app.utils.logger import log


class StorageServiceTests(unittest.TestCase):
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
        self.storage = StorageService(db_path=self.db_path)

    def tearDown(self):
        self.storage.close()
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except PermissionError:
                pass

    def test_create_table_also_creates_indexes(self):
        with sqlite3.connect(self.db_path) as conn:
            names = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_counts_%'"
                ).fetchall()
            }

        self.assertIn("idx_counts_timestamp", names)
        self.assertIn("idx_counts_direction_timestamp", names)

    def test_save_count_flushes_when_batch_size_reached(self):
        self.storage._batch_size = 2
        self.storage.save_count("IN", 1)
        self.storage.save_count("OUT", 2)

        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM counts").fetchone()[0]

        self.assertEqual(total, 2)

    def test_close_flushes_pending_buffer(self):
        self.storage._batch_size = 100
        self.storage.save_count("IN", 123)
        self.storage.close()

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT direction, object_id FROM counts").fetchall()

        self.assertEqual(rows, [("IN", 123)])


if __name__ == "__main__":
    unittest.main()
