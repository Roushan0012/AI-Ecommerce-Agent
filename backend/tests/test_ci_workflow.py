import re
from pathlib import Path
import pytest
from app.core.config import Settings, settings


def test_ci_workflow_file_exists_and_configured():
    """Verify that .github/workflows/ci.yml exists and contains expected structure."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    ci_file = repo_root / ".github" / "workflows" / "ci.yml"

    assert ci_file.exists(), "CI workflow file .github/workflows/ci.yml must exist"

    content = ci_file.read_text(encoding="utf-8")

    # 1. Triggers
    assert "push:" in content, "Workflow must trigger on push"
    assert "pull_request:" in content, "Workflow must trigger on pull_request"
    assert "main" in content, "Workflow triggers must target main branch"

    # 2. Jobs
    assert "backend-tests:" in content, "Workflow must include backend-tests job"
    assert "frontend-build:" in content, "Workflow must include frontend-build job"
    assert "ubuntu-latest" in content, "Workflow should run on ubuntu-latest runners"

    # 3. Backend Steps
    assert "actions/setup-python" in content, "Backend job must set up Python"
    assert "requirements.txt" in content, "Backend job must reference requirements.txt"
    assert "pytest" in content, "Backend job must run pytest"

    # 4. Frontend Steps
    assert "actions/setup-node" in content, "Frontend job must set up Node.js"
    assert "package-lock.json" in content, "Frontend job must cache package-lock.json"
    assert "npm ci" in content, "Frontend job must install dependencies with npm ci"
    assert "npm run build" in content, "Frontend job must execute npm run build"


def test_ci_workflow_zero_secrets_hygiene():
    """Verify that no sensitive production credentials or real API tokens exist in the workflow."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    ci_file = repo_root / ".github" / "workflows" / "ci.yml"

    content = ci_file.read_text(encoding="utf-8")

    # Forbidden patterns in CI workflow
    forbidden_patterns = [
        r"rzp_live_[a-zA-Z0-9]+",
        r"gsk_[a-zA-Z0-9]+",
        r"ghp_[a-zA-Z0-9]+",
        r"eyJ[a-zA-Z0-9_-]{20,}",  # Real JWT token format
        r"BEGIN (RSA|EC|OPENSSH|PGP) PRIVATE KEY",
        r"supabase\.co",
        r"postgres://",
        r"postgresql://",
    ]

    for pattern in forbidden_patterns:
        match = re.search(pattern, content)
        assert not match, f"Found forbidden sensitive pattern '{pattern}' in ci.yml: {match}"


def test_test_environment_settings_safe_defaults(monkeypatch):
    """Verify that settings provide safe test defaults without needing production secrets."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("COMMERCE_AGENT_KEY", raising=False)
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("RAZORPAY_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    s = Settings()
    assert s.is_test, "Settings must resolve to test mode"
    assert s.ENVIRONMENT == "test"
    assert not s.DEBUG, "Debug should be false in test mode"
    assert s.AI_PROVIDER == "mock"
    assert s.COMMERCE_AGENT_KEY == s.INSECURE_DEV_AGENT_KEY
    assert s.RAZORPAY_KEY_ID == s.INSECURE_DEV_RAZORPAY_KEY_ID
    assert s.RAZORPAY_WEBHOOK_SECRET == s.INSECURE_DEV_RAZORPAY_WEBHOOK_SECRET
    assert s.JWT_SECRET_KEY == s.INSECURE_DEV_JWT_SECRET
