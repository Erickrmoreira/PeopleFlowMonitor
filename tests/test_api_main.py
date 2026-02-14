import unittest

try:
    from fastapi.testclient import TestClient
    from app.api.main import app, get_stats_analyzer
    FASTAPI_AVAILABLE = True
except Exception:
    TestClient = None
    app = None
    get_stats_analyzer = None
    FASTAPI_AVAILABLE = False


class _FakeStatsAnalyzer:
    def get_daily_report(self):
        return {"IN": 7, "OUT": 3}


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi nao esta instalado no ambiente")


class ApiMainTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[get_stats_analyzer] = lambda: _FakeStatsAnalyzer()
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})

    def test_stats_endpoint_uses_dependency(self):
        response = self.client.get("/stats")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "today": {"IN": 7, "OUT": 3},
                "unit": "people",
            },
        )


if __name__ == "__main__":
    unittest.main()
