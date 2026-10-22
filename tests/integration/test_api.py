"""Tests for FastAPI endpoints."""

import logging

import pytest
from fastapi.testclient import TestClient
from splicegaip.api.app import create_app


@pytest.fixture
def client():
    """Create test client for API endpoints."""
    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """The API health endpoint returns a ready status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"

    def test_health_returns_version(self, client):
        """Test health endpoint includes version info."""
        response = client.get("/api/health")
        data = response.json()
        assert data["version"]


class TestRootEndpoint:
    """Test root endpoint."""

    def test_root_endpoint(self, client):
        """The root endpoint serves the browser application."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "SpliceGAIP" in response.text


class TestFavicon:
    """Test favicon endpoint."""

    def test_favicon_endpoint(self, client):
        """Test /favicon.ico returns SVG."""
        response = client.get("/favicon.ico")
        assert response.status_code == 200
        assert "svg" in response.headers.get("content-type", "").lower()


class TestProjectEndpoints:
    """Test project management endpoints."""

    def test_list_projects_empty(self, client):
        """Test listing projects when none exist."""
        response = client.get("/api/projects")
        # Should not crash even if no projects exist
        assert response.status_code in [200, 404]

    def test_project_status_invalid(self, client):
        """Test project status with invalid ID."""
        response = client.get("/api/status/invalid-id")
        assert response.status_code == 404


class TestAnalyzeEndpoint:
    """Test analysis endpoint."""

    def test_analyze_missing_input(self, client):
        """Test analyze without input file."""
        response = client.post("/api/analyze", json={})
        assert response.status_code == 400

    def test_analyze_with_invalid_query(self, client):
        """Test analyze with empty query."""
        response = client.post(
            "/api/analyze",
            json={"query": ""},
        )
        assert response.status_code == 400


class TestReportEndpoint:
    """Test report generation endpoints."""

    def test_report_not_found(self, client):
        """Test report for non-existent project."""
        response = client.get("/api/report/invalid-id")
        assert response.status_code == 404


class TestAPIErrorHandling:
    """Test API error handling."""

    def test_404_handler(self, client):
        """Test 404 handler for unknown routes."""
        response = client.get("/nonexistent-route")
        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """Test method not allowed."""
        # POST to GET-only endpoint
        response = client.post("/api/health")
        assert response.status_code == 405

    def test_debug_endpoint_does_not_log_auth_header(self, client, caplog):
        """Debug logging must not capture bearer/API credentials."""
        caplog.set_level(logging.INFO)
        response = client.post(
            "/api/upload-debug",
            headers={"Authorization": "Bearer do-not-log-this"},
            data={},
        )
        assert response.status_code == 200
        assert "do-not-log-this" not in caplog.text


class TestAPIHeaders:
    """Test API response headers."""

    def test_content_type_json(self, client):
        """Test JSON endpoints return correct content type."""
        response = client.get("/api/health")
        assert "application/json" in response.headers.get("content-type", "")

    def test_openapi_documentation(self, client):
        """The generated OpenAPI document exposes the public API contract."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert response.json()["info"]["title"] == "SpliceGAIP API"

    def test_security_and_request_headers(self, client):
        """Responses expose a correlation id and baseline browser hardening."""
        response = client.get("/api/health")
        assert response.headers["x-request-id"]
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"


class TestAPIKeyAuthentication:
    """API key protection is opt-in for deployments exposed beyond localhost."""

    def test_configured_key_protects_api_routes(self, monkeypatch):
        monkeypatch.setenv("SPLICEGAIP_API_KEY", "test-secret")
        protected_client = TestClient(create_app())

        assert protected_client.get("/api/projects").status_code == 401
        assert protected_client.get(
            "/api/projects", headers={"X-API-Key": "wrong"}
        ).status_code == 401
        assert protected_client.get(
            "/api/projects", headers={"X-API-Key": "test-secret"}
        ).status_code == 200

    def test_health_remains_available_for_probes(self, monkeypatch):
        monkeypatch.setenv("SPLICEGAIP_API_KEY", "test-secret")
        protected_client = TestClient(create_app())

        assert protected_client.get("/api/health").status_code == 200


class TestAPIRateLimit:
    """Rate limiting is opt-in for deployments exposed beyond localhost."""

    def test_configured_rate_limit_returns_retry_after(self, monkeypatch):
        monkeypatch.setenv("SPLICEGAIP_RATE_LIMIT", "2")
        limited_client = TestClient(create_app())

        assert limited_client.get("/api/projects").status_code == 200
        assert limited_client.get("/api/projects").status_code == 200
        response = limited_client.get("/api/projects")

        assert response.status_code == 429
        assert int(response.headers["retry-after"]) >= 1
        assert limited_client.get("/api/health").status_code == 200
