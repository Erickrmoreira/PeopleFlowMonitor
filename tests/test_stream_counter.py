import unittest
from time import monotonic
from types import SimpleNamespace
from unittest.mock import patch

from app.analytics.counter import StreamCounter
from app.core.enums import Position
from app.utils.logger import log


class _FakeTensor:
    def __init__(self, data):
        self.data = data

    def cpu(self):
        return self

    def numpy(self):
        return self.data

    def int(self):
        return _FakeTensor([int(x) for x in self.data])

    def __getitem__(self, key):
        if isinstance(key, tuple):
            rows, col = key
            selected = self.data[rows] if isinstance(rows, slice) else [self.data[rows]]
            return _FakeTensor([row[col] for row in selected])
        return _FakeTensor(self.data[key])


class _FakeBoxes:
    def __init__(self, y_tops, ids):
        self.xyxy = _FakeTensor([[0.0, float(y), 10.0, float(y) + 10.0] for y in y_tops])
        self.id = _FakeTensor(ids)

    def __bool__(self):
        return len(self.id.data) > 0


class _FakeStorageService:
    def __init__(self):
        self.saved_events = []

    def save_count(self, direction, object_id):
        self.saved_events.append((direction, object_id))


class _FakeStatsAnalyzer:
    def get_daily_report(self):
        return {"IN": 0, "OUT": 0}


def _make_results(y_tops, ids):
    return SimpleNamespace(boxes=_FakeBoxes(y_tops, ids))


class StreamCounterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._prev_log_disabled = log.disabled
        log.disabled = True

    @classmethod
    def tearDownClass(cls):
        log.disabled = cls._prev_log_disabled

    def _make_counter(self):
        config = {
            "counting_line": {
                "y_ratio": 0.5,
                "offset": 0.05,
                "max_inactive_seconds": 0.1,
            }
        }
        with patch("app.analytics.counter.load_zones_config", return_value=config), patch(
            "app.analytics.counter.StorageService", _FakeStorageService
        ), patch("app.analytics.counter.StatsAnalyzer", _FakeStatsAnalyzer):
            counter = StreamCounter()
        counter.cleanup_interval_seconds = 0.0
        return counter

    def test_in_out_and_anti_duplication(self):
        counter = self._make_counter()
        frame_shape = (100, 100, 3)

        counter.count(_make_results([40], [1]), frame_shape)  # TOP
        in_c, out_c = counter.count(_make_results([60], [1]), frame_shape)  # TOP -> BOTTOM (IN)
        self.assertEqual((in_c, out_c), (1, 0))

        in_c, out_c = counter.count(_make_results([40], [1]), frame_shape)  # already counted, no OUT
        self.assertEqual((in_c, out_c), (1, 0))

        counter.count(_make_results([60], [2]), frame_shape)  # BOTTOM
        in_c, out_c = counter.count(_make_results([40], [2]), frame_shape)  # BOTTOM -> TOP (OUT)
        self.assertEqual((in_c, out_c), (1, 1))

        self.assertEqual(counter.storage.saved_events, [("IN", 1), ("OUT", 2)])

    def test_cleanup_removes_stale_ids(self):
        counter = self._make_counter()
        frame_shape = (100, 100, 3)

        counter.track_positions[99] = Position.TOP
        counter.already_counted.add(99)
        counter.last_seen_at[99] = monotonic() - 5.0

        counter.count(SimpleNamespace(boxes=None), frame_shape)

        self.assertNotIn(99, counter.track_positions)
        self.assertNotIn(99, counter.already_counted)
        self.assertNotIn(99, counter.last_seen_at)


if __name__ == "__main__":
    unittest.main()
