"""Phase 18D — Frontend Production Configuration & Contract Tests.

Validates:
1. Backend contract for frontend authentication (GET /api/auth/me)
2. Frontend environment configuration safety (.env.example, no exposed secrets)
3. Role-based access control alignment between frontend and backend
4. Strict decoupling: frontend never possesses or transmits machine keys (COMMERCE_AGENT_KEY / X-Agent-Key)
"""

import os
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, get_current_user, hash_password
from app.main import app
from app.models.user import User, UserRole


def test_auth_me_contract_with_valid_token():
    """GET /api/auth/me returns authoritative user profile for valid Bearer token."""
    app.dependency_overrides.pop(get_current_user, None)
    client = TestClient(app)

    cust_email = f"frontend_user_{uuid.uuid4()}@example.com"
    reg_res = client.post(
        "/api/auth/register",
        json={"email": cust_email, "password": "FrontendPassword123!"},
    )
    assert reg_res.status_code == 201
    user_id = reg_res.json()["id"]

    token = create_access_token(user_id, additional_claims={"role": "customer"})

    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    data = me_res.json()
    assert data["id"] == user_id
    assert data["email"] == cust_email
    assert data["role"] == "customer"
    assert data["is_active"] is True
    assert "password" not in data
    assert "password_hash" not in data


def test_auth_me_contract_rejects_missing_and_forged_tokens():
    """GET /api/auth/me returns 401 for missing, malformed, or forged tokens."""
    client = TestClient(app)

    # Missing Authorization header
    res_missing = client.get("/api/auth/me")
    assert res_missing.status_code == 401

    # Forged signature
    res_forged = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.bogus_sig"},
    )
    assert res_forged.status_code == 401


def test_dashboard_endpoint_requires_merchant_or_admin_role():
    """Backend strictly enforces merchant/admin role for dashboard endpoints."""
    app.dependency_overrides.pop(get_current_user, None)
    client = TestClient(app)

    # 1. Customer account -> 403 Forbidden
    cust_email = f"cust_dash_{uuid.uuid4()}@example.com"
    reg_res = client.post(
        "/api/auth/register",
        json={"email": cust_email, "password": "Password123!"},
    )
    assert reg_res.status_code == 201
    cust_id = reg_res.json()["id"]
    cust_token = create_access_token(cust_id, additional_claims={"role": "customer"})

    dash_res_cust = client.get(
        "/api/dashboard/overview",
        headers={"Authorization": f"Bearer {cust_token}"},
    )
    assert dash_res_cust.status_code == 403

    # 2. Unauthenticated request -> 401 Unauthorized
    dash_res_unauth = client.get("/api/dashboard/overview")
    assert dash_res_unauth.status_code == 401


def test_frontend_env_example_safety():
    """frontend/.env.example must exist and never expose backend secrets."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    env_example_path = repo_root / "frontend" / ".env.example"

    assert env_example_path.exists(), "frontend/.env.example must exist"
    content = env_example_path.read_text(encoding="utf-8")

    assert "NEXT_PUBLIC_API_BASE_URL=" in content
    assert "NEXT_PUBLIC_RAZORPAY_KEY_ID=" in content

    # Backend secrets must NEVER be present
    forbidden_tokens = [
        "JWT_SECRET_KEY=",
        "RAZORPAY_KEY_SECRET=",
        "RAZORPAY_WEBHOOK_SECRET=",
        "DATABASE_URL=",
        "COMMERCE_AGENT_KEY=",
    ]
    for token in forbidden_tokens:
        assert token not in content, f"Forbidden secret '{token}' found in frontend/.env.example"


def test_frontend_source_boundary_no_agent_keys():
    """Frontend source files must never contain machine COMMERCE_AGENT_KEY or X-Agent-Key header."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    src_dir = repo_root / "frontend" / "src"

    assert src_dir.exists(), "frontend/src must exist"

    for file_path in src_dir.rglob("*"):
        if file_path.suffix in (".ts", ".tsx", ".js", ".jsx"):
            content = file_path.read_text(encoding="utf-8")
            assert "COMMERCE_AGENT_KEY" not in content, f"Forbidden COMMERCE_AGENT_KEY in {file_path}"
            assert "X-Agent-Key" not in content, f"Forbidden X-Agent-Key in {file_path}"
