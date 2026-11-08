"""Automated security audit tests for Phase 2 hardening."""
import pytest
from httpx import ASGITransport, AsyncClient
from app.config import AppSettings, settings
from app.main import app


@pytest.mark.asyncio
async def test_voice_agent_status_does_not_expose_sip_passwords():
    """Verify GAP-05: SIP passwords are never leaked in status payloads."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/voice-agent/status")
        assert response.status_code == 200
        data = response.json()
        assert "test_extensions" in data
        for ext in data["test_extensions"]:
            assert "password" not in ext, f"Plaintext password leaked in extension {ext}!"
            assert "ext" in ext
            assert "status" in ext


@pytest.mark.asyncio
async def test_protected_endpoints_require_admin_auth():
    """Verify GAP-06: Unauthenticated requests to administrative routes are blocked (401)."""
    endpoints = [
        ("GET", "/api/v1/calls"),
        ("GET", "/api/v1/calls/some-call-id"),
        ("GET", "/api/v1/farmer/profile"),
        ("GET", "/api/v1/admin/analytics"),
        ("GET", "/api/v1/analytics/overview"),
        ("GET", "/api/v1/developer/sms"),
        ("GET", "/api/v1/telephony/logs"),
        ("DELETE", "/api/v1/telephony/logs"),
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for method, path in endpoints:
            if method == "GET":
                res = await client.get(path)
            elif method == "DELETE":
                res = await client.delete(path)
            assert res.status_code == 401, f"Endpoint {method} {path} unexpectedly allowed unauthenticated access (got {res.status_code})!"
            assert "detail" in res.json()


@pytest.mark.asyncio
async def test_authenticated_admin_access_with_bearer_or_x_admin_key():
    """Verify that requests with valid admin credentials succeed."""
    valid_key = settings.ADMIN_API_KEY
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Bearer Token
        res_bearer = await client.get(
            "/api/v1/telephony/logs",
            headers={"Authorization": f"Bearer {valid_key}"},
        )
        assert res_bearer.status_code == 200

        # 2. X-Admin-Key Header
        res_header = await client.get(
            "/api/v1/telephony/logs",
            headers={"X-Admin-Key": valid_key},
        )
        assert res_header.status_code == 200

        # 3. Invalid credentials must return 401
        res_invalid = await client.get(
            "/api/v1/telephony/logs",
            headers={"Authorization": "Bearer wrong-token-123"},
        )
        assert res_invalid.status_code == 401


def test_cors_settings_disallows_wildcard_with_credentials():
    """Verify GAP-09: Wildcard origin is not used when allow_credentials is True."""
    assert "*" not in settings.ALLOWED_ORIGINS
    assert "http://localhost:3000" in settings.ALLOWED_ORIGINS


def test_production_environment_fails_fast_on_insecure_defaults():
    """Verify GAP-10: Insecure development keys raise ValueError in production."""
    prod_settings = AppSettings(
        ENVIRONMENT="production",
        SECRET_KEY="hello_farmer_insecure_dev_secret_change_me_32chars!",
        PHONE_ENCRYPTION_KEY="D7L2j61X01c90wPZq8c1BvK7x8k1D2M4N6P8Q0R2S4T=",
    )
    with pytest.raises(ValueError, match="CRITICAL SECURITY ERROR"):
        prod_settings.validate_production_secrets()

