import unittest
import types
import sys

if "cv2" not in sys.modules:
    sys.modules["cv2"] = types.ModuleType("cv2")
if "ultralytics" not in sys.modules:
    ultralytics_stub = types.ModuleType("ultralytics")
    ultralytics_stub.YOLO = object
    sys.modules["ultralytics"] = ultralytics_stub

from app.core.pipeline import ProcessingPipeline
from app.utils.logger import log


class _FailingTracker:
    def update(self, detector, frame):
        raise RuntimeError("tracker error")


class _UnusedCounter:
    def count(self, results, frame_shape):
        return (999, 999)


class PipelineFallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._prev_log_disabled = log.disabled
        log.disabled = True

    @classmethod
    def tearDownClass(cls):
        log.disabled = cls._prev_log_disabled

    def test_process_frame_keeps_last_counts_on_tracker_exception(self):
        pipeline = ProcessingPipeline.__new__(ProcessingPipeline)
        pipeline.tracker = _FailingTracker()
        pipeline.counter = _UnusedCounter()
        pipeline.detector = object()

        last_results = object()
        last_counts = (7, 3)

        results, in_c, out_c = pipeline._process_frame(
            frame=object(),
            last_results=last_results,
            last_counts=last_counts,
        )

        self.assertIs(results, last_results)
        self.assertEqual((in_c, out_c), last_counts)


if __name__ == "__main__":
    unittest.main()
