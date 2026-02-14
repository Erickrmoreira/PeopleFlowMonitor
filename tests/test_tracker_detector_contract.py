import unittest

from app.tracking.tracker import PersonTracker


class _FakeDetector:
    def __init__(self):
        self.calls = []

    def track(self, frame, tracker, conf, iou):
        self.calls.append(
            {
                "frame": frame,
                "tracker": tracker,
                "conf": conf,
                "iou": iou,
            }
        )
        return {"ok": True}


class PersonTrackerContractTests(unittest.TestCase):
    def test_update_uses_detector_track_contract(self):
        detector = _FakeDetector()
        tracker = PersonTracker(tracker_config="botsort.yaml", conf=0.25, iou=0.45)
        frame = object()

        result = tracker.update(detector, frame)

        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(detector.calls), 1)
        self.assertEqual(detector.calls[0]["frame"], frame)
        self.assertEqual(detector.calls[0]["tracker"], "botsort.yaml")
        self.assertEqual(detector.calls[0]["conf"], 0.25)
        self.assertEqual(detector.calls[0]["iou"], 0.45)


if __name__ == "__main__":
    unittest.main()
