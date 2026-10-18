"""
Offline Unit Test for API Health Endpoint (api/test_api_health.py)
-------------------------------------------------------------------
Tests the resilient /api/health endpoint with mocked database success and failure.
Verifies no credentials, internal IPs, or stack traces are leaked on database downtime.
Does NOT connect to FalkorDB or use the network.
"""

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health_success():
    """Verify health endpoint when database returns valid count."""
    with patch("graph.queries.run", return_value=([{"nodes": 42}], {})):
        response = client.get("/api/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("ok") is True
        assert data.get("nodes") == 42
        assert "error" not in data
    print("PASS: test_health_success")


def test_health_database_failure():
    """Verify health endpoint when database raises ConnectionError or timeout."""
    with patch("graph.queries.run", side_effect=ConnectionError("FalkorDB host 10.0.0.1 unreachable: timeout")):
        response = client.get("/api/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("ok") is False
        assert data.get("nodes") == 0
        assert data.get("error") == "database_unavailable"
        assert data.get("detail") == "Graph database unreachable"
        # Zero-leakage assertions: no internal IPs, passwords, or raw exceptions in response
        raw_text = response.text
        assert "10.0.0.1" not in raw_text, "Leaked internal IP"
        assert "Traceback" not in raw_text, "Leaked stack trace"
        assert "ConnectionError" not in raw_text, "Leaked exception name"
    print("PASS: test_health_database_failure (clean fallback, zero information leakage)")


if __name__ == "__main__":
    print("Running API health offline tests...")
    test_health_success()
    test_health_database_failure()
    print("ALL API HEALTH TESTS PASSED CLEANLY (2/2)")
