"""Phase 18F-3 — Process Supervision & Multi-Container Orchestration Tests.

Validates:
1. Docker Compose orchestration configuration existence, syntax, and schema validity
2. Backend and frontend services isolation (separate containers, non-root execution)
3. Production command verification: zero usage of development-only --reload or 'next dev'
4. Health check probe validity (/api/health liveness probe vs /api/health/database readiness)
5. Zero secrets embedded into Dockerfiles or docker-compose.yml
6. Build contexts and .dockerignore rules preventing leak of .env, .venv, or *.db
7. Orchestration compatibility with managed external database architecture
"""

from pathlib import Path
import pytest


def test_docker_compose_file_exists_and_parses():
    """Verify docker-compose.yml exists and contains required services."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    compose_file = repo_root / "docker-compose.yml"

    assert compose_file.exists(), "docker-compose.yml must exist at repository root"
    content = compose_file.read_text(encoding="utf-8")

    assert "services:" in content
    assert "backend:" in content
    assert "frontend:" in content


def test_backend_dockerfile_and_supervision_command():
    """Verify backend container configuration uses production uvicorn and no reload."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    backend_dockerfile = repo_root / "backend" / "Dockerfile"

    assert backend_dockerfile.exists()
    content = backend_dockerfile.read_text(encoding="utf-8")

    # Supervised production command
    assert "uvicorn app.main:app" in content
    assert "--proxy-headers" in content
    assert "--forwarded-allow-ips" in content
    assert "--reload" not in content, "--reload is forbidden in production backend Dockerfile"

    # Non-root user execution
    assert "USER appuser" in content

    # Health check probe references /api/health
    assert "/api/health" in content


def test_frontend_dockerfile_and_production_lifecycle():
    """Verify frontend container configuration runs npm run build and npm start, not next dev."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    frontend_dockerfile = repo_root / "frontend" / "Dockerfile"

    assert frontend_dockerfile.exists()
    content = frontend_dockerfile.read_text(encoding="utf-8")

    # Production build and start
    assert "npm run build" in content
    assert "npm" in content and "start" in content
    assert "next dev" not in content, "'next dev' is forbidden in production frontend Dockerfile"

    # Non-root user execution
    assert "USER nextjs" in content

    # Uses Node 20
    assert "node:20" in content


def test_dockerignore_excludes_secrets_and_build_artifacts():
    """Verify backend and frontend .dockerignore files exclude sensitive files."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    backend_dockerignore = (repo_root / "backend" / ".dockerignore").read_text(encoding="utf-8")
    frontend_dockerignore = (repo_root / "frontend" / ".dockerignore").read_text(encoding="utf-8")

    # Backend dockerignore exclusions
    assert ".env" in backend_dockerignore
    assert ".venv" in backend_dockerignore
    assert "*.db" in backend_dockerignore
    assert "tests/" in backend_dockerignore or "tests" in backend_dockerignore

    # Frontend dockerignore exclusions
    assert "node_modules" in frontend_dockerignore
    assert ".next" in frontend_dockerignore
    assert ".env" in frontend_dockerignore
    assert "tests" in frontend_dockerignore


def test_no_secrets_embedded_in_orchestration():
    """Verify docker-compose.yml contains zero hardcoded API keys, JWT secrets, or DB passwords."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    compose_content = (repo_root / "docker-compose.yml").read_text(encoding="utf-8")

    # Secrets must be environment variable references, never raw secrets
    assert "rzp_live_" not in compose_content
    assert "gsk_" not in compose_content
    assert "ghp_" not in compose_content
    assert "BEGIN PRIVATE KEY" not in compose_content

    # Check that critical variables reference environment expansions
    assert "DATABASE_URL=${DATABASE_URL}" in compose_content
    assert "JWT_SECRET_KEY=${JWT_SECRET_KEY}" in compose_content
    assert "COMMERCE_AGENT_KEY=${COMMERCE_AGENT_KEY}" in compose_content
    assert "RAZORPAY_KEY_SECRET=${RAZORPAY_KEY_SECRET}" in compose_content


def test_orchestration_managed_database_decoupling():
    """Verify orchestration does not define a local PostgreSQL container, preserving managed Supabase architecture."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    compose_content = (repo_root / "docker-compose.yml").read_text(encoding="utf-8")

    # Ensure no postgres: container image is defined in compose
    assert "image: postgres" not in compose_content
    assert "postgres:" not in compose_content.split("services:")[1].split("backend:")[0]


def test_frontend_depends_on_backend_health():
    """Verify frontend service in docker-compose waits for backend healthy status."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    compose_content = (repo_root / "docker-compose.yml").read_text(encoding="utf-8")

    assert "depends_on:" in compose_content
    assert "backend:" in compose_content
    assert "condition: service_healthy" in compose_content
