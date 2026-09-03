"""Phase 18B CI Workflow and Failure-Safety Hardening Tests.

Validates:
- CI workflow YAML syntax and top-level configuration
- Workflow triggers (push, pull_request, workflow_dispatch) targeting main
- Job names and runners (backend-tests, frontend-build on ubuntu-latest)
- Failure-safety: no continue-on-error, deterministic shell execution, error propagation
- Dependency determinism: requirements.txt with pip caching, npm ci with npm caching
- Environment isolation: test mode defaults, unbuffered logs, no production secrets
- Security hygiene: zero credentials, zero secret leakage, no artifact uploads
- Git isolation: .gitignore enforces exclusion of .env and secret files
- Safeguards integrity: production config validation remains strict and unweakened
"""

import os
import re
import subprocess
from pathlib import Path
import pytest
from app.core.config import Settings, settings, ConfigurationError

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def get_ci_workflow_path() -> Path:
    repo_root = Path(__file__).resolve().parent.parent.parent
    ci_file = repo_root / ".github" / "workflows" / "ci.yml"
    return ci_file


def load_ci_workflow():
    ci_file = get_ci_workflow_path()
    assert ci_file.exists(), "CI workflow file .github/workflows/ci.yml must exist"
    content = ci_file.read_text(encoding="utf-8")
    parsed = yaml.safe_load(content) if yaml else None
    return content, parsed


# ==============================================================================
# 1. CI Workflow Structure & YAML Validation
# ==============================================================================

def test_ci_workflow_structure_and_yaml_validity():
    """Verify that .github/workflows/ci.yml is valid YAML and correctly configured."""
    content, parsed = load_ci_workflow()

    assert "name: CI Pipeline" in content
    assert "push:" in content
    assert "pull_request:" in content
    assert "workflow_dispatch:" in content

    # Check top-level security permissions
    assert "permissions:" in content
    assert "contents: read" in content

    # Check concurrency cancellation configuration
    assert "concurrency:" in content
    assert "cancel-in-progress:" in content

    # Check default shell
    assert "defaults:" in content
    assert "shell: bash" in content

    # Verify structured YAML if parser is available
    if parsed:
        assert parsed.get("name") == "CI Pipeline"
        # In YAML 1.1, 'on' key parses as boolean True
        triggers = parsed.get(True) or parsed.get("on")
        assert triggers is not None, "Workflow triggers must be defined"
        assert "push" in triggers
        assert "pull_request" in triggers
        assert "workflow_dispatch" in triggers
        assert "main" in triggers["push"]["branches"]
        assert "main" in triggers["pull_request"]["branches"]

        permissions = parsed.get("permissions")
        assert permissions == {"contents": "read"}

        concurrency = parsed.get("concurrency")
        assert concurrency is not None
        assert "cancel-in-progress" in concurrency

        defaults = parsed.get("defaults", {}).get("run", {})
        assert defaults.get("shell") == "bash"

        jobs = parsed.get("jobs", {})
        assert "backend-tests" in jobs
        assert "frontend-build" in jobs


# ==============================================================================
# 2. CI Failure-Safety & Error Propagation
# ==============================================================================

def test_ci_failure_propagation_and_no_continue_on_error():
    """Verify that CI steps do not suppress errors and fail-fast when errors occur."""
    content, parsed = load_ci_workflow()

    # Neither job nor any step should have continue-on-error: true
    assert "continue-on-error: true" not in content, "Workflow must not suppress failures with continue-on-error"
    assert "continue-on-error" not in content, "Workflow must not have continue-on-error configured on required validations"

    # Verify shell commands do not swallow exit codes
    forbidden_swallow_patterns = [
        r"\|\|\s*true",
        r"\|\|\s*exit\s+0",
        r";\s*exit\s+0",
        r"set\s+\+e",
    ]
    for pattern in forbidden_swallow_patterns:
        match = re.search(pattern, content)
        assert not match, f"Found error-swallowing pattern '{pattern}' in ci.yml: {match}"

    # Verify pytest and npm run build are executed directly
    assert "pytest -v" in content
    assert "npm run build" in content

    if parsed:
        jobs = parsed.get("jobs", {})
        for job_id, job in jobs.items():
            assert "continue-on-error" not in job, f"Job '{job_id}' must not have continue-on-error"
            for step in job.get("steps", []):
                assert "continue-on-error" not in step, f"Step '{step.get('name')}' in job '{job_id}' must not have continue-on-error"


# ==============================================================================
# 3. Backend Job Determinism & Environment Isolation
# ==============================================================================

def test_backend_job_determinism_and_environment():
    """Verify backend job uses deterministic dependencies, pip caching, and test isolation."""
    content, parsed = load_ci_workflow()

    assert "backend-tests:" in content
    assert "actions/setup-python@v5" in content
    assert "python-version: '3.12'" in content
    assert "cache: 'pip'" in content
    assert "cache-dependency-path: backend/requirements.txt" in content

    assert "pip install -r backend/requirements.txt" in content
    assert "pytest -v" in content

    # Environment isolation checks
    assert "ENVIRONMENT: test" in content
    assert "DATABASE_URL: sqlite:///./ci_test.db" in content
    assert "AI_PROVIDER: mock" in content
    assert "PYTHONUNBUFFERED: '1'" in content
    assert "PYTHONDONTWRITEBYTECODE: '1'" in content

    if parsed:
        backend_job = parsed["jobs"]["backend-tests"]
        assert backend_job.get("runs-on") == "ubuntu-latest"
        steps = backend_job.get("steps", [])

        # Verify setup-python step
        setup_step = next((s for s in steps if "setup-python" in s.get("uses", "")), None)
        assert setup_step is not None
        assert setup_step["with"]["python-version"] == "3.12"
        assert setup_step["with"]["cache"] == "pip"

        # Verify test step env
        test_step = next((s for s in steps if "pytest" in s.get("run", "")), None)
        assert test_step is not None
        step_env = test_step.get("env", {})
        assert step_env.get("ENVIRONMENT") == "test"
        assert step_env.get("AI_PROVIDER") == "mock"
        assert "sqlite" in step_env.get("DATABASE_URL", "")


# ==============================================================================
# 4. Frontend Job Determinism & Environment Isolation
# ==============================================================================

def test_frontend_job_determinism_and_environment():
    """Verify frontend job uses locked npm dependencies, npm caching, and safe env."""
    content, parsed = load_ci_workflow()

    assert "frontend-build:" in content
    assert "actions/setup-node@v4" in content
    assert "node-version: '20'" in content
    assert "cache: 'npm'" in content
    assert "cache-dependency-path: frontend/package-lock.json" in content

    assert "npm ci" in content, "Frontend install must use npm ci for locked reproducible dependencies"
    assert "npm run build" in content

    assert "CI: 'true'" in content
    assert "NEXT_TELEMETRY_DISABLED: '1'" in content
    assert "NEXT_PUBLIC_API_BASE_URL: http://127.0.0.1:8000" in content

    if parsed:
        frontend_job = parsed["jobs"]["frontend-build"]
        assert frontend_job.get("runs-on") == "ubuntu-latest"
        steps = frontend_job.get("steps", [])

        # Verify setup-node step
        setup_step = next((s for s in steps if "setup-node" in s.get("uses", "")), None)
        assert setup_step is not None
        assert setup_step["with"]["node-version"] == "20"
        assert setup_step["with"]["cache"] == "npm"

        # Verify install step
        install_step = next((s for s in steps if "npm ci" in s.get("run", "")), None)
        assert install_step is not None
        assert install_step.get("working-directory") == "frontend"

        # Verify build step
        build_step = next((s for s in steps if "npm run build" in s.get("run", "")), None)
        assert build_step is not None
        assert build_step.get("working-directory") == "frontend"
        step_env = build_step.get("env", {})
        assert step_env.get("CI") == "true"
        assert step_env.get("NEXT_TELEMETRY_DISABLED") == "1"


# ==============================================================================
# 5. Zero Secrets & Artifact Safety Hygiene
# ==============================================================================

def test_ci_workflow_zero_secrets_and_artifacts_hygiene():
    """Verify that CI workflow exposes no secrets and uploads no sensitive artifacts."""
    content, parsed = load_ci_workflow()

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

    # CI must not upload artifacts (no upload-artifact actions)
    assert "actions/upload-artifact" not in content, "CI must not upload build or environment artifacts"

    # CI must never print or echo .env contents
    assert "cat .env" not in content
    assert "echo $.env" not in content
    assert "printenv" not in content


# ==============================================================================
# 6. Git Isolation & Secret Exclusion
# ==============================================================================

def test_gitignore_enforces_env_and_secret_isolation():
    """Verify that .gitignore excludes .env files, private keys, and build artifacts."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    root_gitignore = repo_root / ".gitignore"
    frontend_gitignore = repo_root / "frontend" / ".gitignore"

    assert root_gitignore.exists()
    root_content = root_gitignore.read_text(encoding="utf-8")
    assert ".env" in root_content
    assert ".env.local" in root_content

    assert frontend_gitignore.exists()
    frontend_content = frontend_gitignore.read_text(encoding="utf-8")
    assert ".env" in frontend_content

    # Confirm via git ls-files that no .env, .pem, or .key files are tracked
    git_result = subprocess.run(
        ["git", "ls-files", "*.env*", "*.pem", "*.key"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    tracked_files = [line.strip() for line in git_result.stdout.strip().splitlines() if line.strip()]
    for path in tracked_files:
        assert path.endswith(".example"), f"Forbidden secret/env file is tracked in git: {path}"


# ==============================================================================
# 7. Safe Test Defaults Isolation
# ==============================================================================

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


# ==============================================================================
# 8. Production Configuration Safeguards Not Weakened
# ==============================================================================

def test_production_configuration_safeguards_not_weakened(monkeypatch):
    """Verify that production security validation remains strictly enforced."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./prod.db")  # SQLite disallowed in prod
    monkeypatch.setenv("JWT_SECRET_KEY", "prod_valid_jwt_secret_key_long_enough_12345")
    monkeypatch.setenv("COMMERCE_AGENT_KEY", "prod_valid_agent_key_12345")
    monkeypatch.setenv("RAZORPAY_KEY_ID", "prod_valid_razorpay_key_id_test")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "prod_key_secret_12345")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "prod_webhook_secret_12345")
    monkeypatch.setenv("CORS_ORIGINS", "https://mystore.com")

    prod_settings = Settings()
    with pytest.raises(ConfigurationError) as exc_info:
        prod_settings.validate_production_config()
    assert "DATABASE_URL" in str(exc_info.value)
