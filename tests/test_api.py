"""
Unit Tests for NetLens Pro REST API Endpoints
Validates health checks, telemetry statistics, flow endpoints, and alert querying.
"""

import unittest
from fastapi.testclient import TestClient
from api.server import app


class TestApiEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_check_endpoint(self):
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("service"), "NetLens Pro")
        self.assertIn("version", data)

    def test_stats_endpoint(self):
        response = self.client.get("/api/v1/stats")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_packets", data)
        self.assertIn("total_bytes", data)
        self.assertIn("packets_per_second", data)
        self.assertIn("bytes_per_second", data)
        self.assertIn("protocol_distribution", data)

    def test_packets_endpoint(self):
        response = self.client.get("/api/v1/packets?limit=25")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("packets", data)
        self.assertEqual(data.get("limit"), 25)

    def test_flows_endpoint(self):
        response = self.client.get("/api/v1/flows")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("flows", data)
        self.assertIn("count", data)

    def test_alerts_endpoint(self):
        response = self.client.get("/api/v1/alerts")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("alerts", data)
        self.assertIn("count", data)


if __name__ == "__main__":
    unittest.main()
