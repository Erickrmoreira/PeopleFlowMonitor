import unittest
import types
import sys

if "ultralytics" not in sys.modules:
    ultralytics_stub = types.ModuleType("ultralytics")
    ultralytics_stub.YOLO = object
    sys.modules["ultralytics"] = ultralytics_stub

from app.detection.yolo_detector import YOLODetector


class _FakeModel:
    def __init__(self):
        self.kwargs = None
        self.frame = None

    def track(self, frame, **kwargs):
        self.frame = frame
        self.kwargs = kwargs
        return ["tracked-result"]


class YOLODetectorTrackTests(unittest.TestCase):
    def test_track_delegates_to_model_and_returns_first_result(self):
        detector = YOLODetector.__new__(YOLODetector)
        detector.model = _FakeModel()

        frame = object()
        result = detector.track(frame, tracker="botsort.yaml", conf=0.4, iou=0.6)

        self.assertEqual(result, "tracked-result")
        self.assertIs(detector.model.frame, frame)
        self.assertEqual(detector.model.kwargs["persist"], True)
        self.assertEqual(detector.model.kwargs["tracker"], "botsort.yaml")
        self.assertEqual(detector.model.kwargs["classes"], [0])
        self.assertEqual(detector.model.kwargs["conf"], 0.4)
        self.assertEqual(detector.model.kwargs["iou"], 0.6)
        self.assertEqual(detector.model.kwargs["verbose"], False)


if __name__ == "__main__":
    unittest.main()
