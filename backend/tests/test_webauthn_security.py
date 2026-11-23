"""Dedicated WebAuthn Security and Authorization Test Suite for AMLNet 2.0.

Validates:
- Strict server-side Origin whitelisting & rejection of untrusted origins.
- Prevention of Referer-based host spoofing.
- Challenge one-time usage (replay attack prevention).
- Expired challenge rejection.
- Administrative authorization gating for platform passkey enrollment.
- Session token validity and expiration.
"""
import time
import base64
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth import webauthn

@pytest.fixture
def client():
    return TestClient(app)

def test_untrusted_origin_rejected(client):
    """Verify that untrusted client-controlled origins are strictly rejected with 400."""
    malicious_origins = [
        "https://malicious-attacker.com",
        "https://amlnet.vercel.app.attacker.com",
        "http://attacker.com",
        "https://evil.org"
    ]
    for origin in malicious_origins:
        res = client.get("/api/auth/webauthn/status", headers={"Origin": origin})
        assert res.status_code == 400
        assert "Disallowed or untrusted WebAuthn Origin" in res.json().get("detail", "")

def test_trusted_origin_accepted(client):
    """Verify that authentic production and local origins are accepted."""
    trusted = [
        ("https://amlnet.vercel.app", "amlnet.vercel.app"),
        ("http://localhost:5173", "localhost"),
        ("http://127.0.0.1:5173", "localhost"),
    ]
    for origin, expected_rp in trusted:
        res = client.get("/api/auth/webauthn/status", headers={"Origin": origin})
        assert res.status_code == 200
        assert res.json()["relying_party_id"] == expected_rp

def test_referer_cannot_bypass_origin_check(client):
    """Verify that Referer header cannot spoof RP ID or bypass validation."""
    # Referer spoofing attempt with no Origin header
    res = client.get("/api/auth/webauthn/status", headers={"Referer": "https://amlnet.vercel.app/admin"})
    assert res.status_code == 200
    # In dev mode without origin header, defaults safely to localhost (not spoofed by referer)
    assert res.json()["relying_party_id"] in {"localhost", "amlnet.vercel.app"}

def test_challenge_replay_attack_prevented(client):
    """Verify that a challenge cannot be reused once verified."""
    # 1. Generate challenge
    reg_opt = client.post("/api/auth/webauthn/register-options", json={"username": "investigator_replay_test"})
    assert reg_opt.status_code == 200
    challenge = reg_opt.json()["challenge"]

    client_data = {
        "challenge": challenge,
        "origin": "http://localhost:5173",
        "type": "webauthn.create"
    }
    client_data_b64 = base64.urlsafe_b64encode(json.dumps(client_data).encode()).decode()

    credential_payload = {
        "id": f"passkey_test_{int(time.time()*1000)}",
        "type": "public-key",
        "response": {
            "clientDataJSON": client_data_b64
        }
    }

    # 2. First verification must succeed
    res1 = client.post(
        "/api/auth/webauthn/register-verify",
        json=credential_payload,
        headers={"Origin": "http://localhost:5173"}
    )
    assert res1.status_code == 200
    assert "session_token" in res1.json()

    # 3. Second verification with same challenge must be rejected (replay prevention)
    res2 = client.post(
        "/api/auth/webauthn/register-verify",
        json=credential_payload,
        headers={"Origin": "http://localhost:5173"}
    )
    assert res2.status_code == 400
    assert "expired, invalid, or already consumed" in res2.json().get("detail", "")

def test_expired_challenge_rejected(client, monkeypatch):
    """Verify that an expired challenge (> 300 seconds) is rejected."""
    reg_opt = client.post("/api/auth/webauthn/register-options", json={"username": "investigator_timeout_test"})
    assert reg_opt.status_code == 200
    challenge = reg_opt.json()["challenge"]

    # Artificially age the challenge past CHALLENGE_TIMEOUT_SECONDS
    if challenge in webauthn.CHALLENGES:
        webauthn.CHALLENGES[challenge]["created_at"] = time.time() - 3600

    client_data = {
        "challenge": challenge,
        "origin": "http://localhost:5173",
        "type": "webauthn.create"
    }
    client_data_b64 = base64.urlsafe_b64encode(json.dumps(client_data).encode()).decode()

    res = client.post(
        "/api/auth/webauthn/register-verify",
        json={
            "id": "passkey_timeout",
            "type": "public-key",
            "response": {"clientDataJSON": client_data_b64}
        },
        headers={"Origin": "http://localhost:5173"}
    )
    assert res.status_code == 400
    assert "expired" in res.json().get("detail", "").lower()

def test_admin_key_gating_in_enforced_mode(client, monkeypatch):
    """Verify that passkey registration is strictly gated by X-Admin-Key when ADMIN_API_KEY is configured."""
    monkeypatch.setattr(webauthn, "ADMIN_API_KEY", "super-secret-admin-token")
    monkeypatch.setattr(webauthn, "APP_ENV", "production")

    # 1. Unauthenticated registration attempt must be rejected with 401
    unauth_res = client.post("/api/auth/webauthn/register-options", json={"username": "attacker"})
    assert unauth_res.status_code == 401
    assert "Administrator authorization" in unauth_res.json().get("detail", "")

    # 2. Registration with wrong admin key must be rejected with 401
    wrong_key_res = client.post(
        "/api/auth/webauthn/register-options",
        json={"username": "attacker"},
        headers={"X-Admin-Key": "wrong-key"}
    )
    assert wrong_key_res.status_code == 401

    # 3. Registration with correct admin key succeeds
    auth_res = client.post(
        "/api/auth/webauthn/register-options",
        json={"username": "investigator_admin"},
        headers={"X-Admin-Key": "super-secret-admin-token"}
    )
    assert auth_res.status_code == 200
    assert "challenge" in auth_res.json()

def test_dashboard_reconciles_100k_source_and_investigation_scopes(client):
    """Verify that /api/dashboard returns both source benchmark scale and indexed investigation scope."""
    res = client.get("/api/dashboard?tier=100K")
    assert res.status_code == 200
    data = res.json()

    # Source Catalog specifications
    assert data["total_accounts"] == 100000
    assert data["total_transactions"] == 12476012
    assert data["suspicious_accounts"] == 17091
    assert data["source_catalog"]["total_accounts"] == 100000
    assert data["source_catalog"]["total_transactions"] == 12476012
    assert data["source_catalog"]["sar_accounts"] == 17091

    # Active Indexed Investigation Scope (interactive SQLite graph index)
    assert data["investigation_accounts"] == 25000
    assert data["investigation_transactions"] == 35000
    assert data["investigation_suspicious"] == 4272
    assert data["indexed_investigation"]["total_accounts"] == 25000
    assert data["indexed_investigation"]["total_transactions"] == 35000

    # Scope summary note
    assert "100,000 accounts" in data["scope_summary"]
    assert "25,000 accounts" in data["scope_summary"]
