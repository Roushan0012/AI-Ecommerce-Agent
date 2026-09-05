# Continuous Integration (CI/CD Pipeline)

## 1. Overview

The AI Commerce Agent Platform uses GitHub Actions for automated continuous integration. Every commit pushed to `main` and every pull request targeting `main` is validated through automated test execution, security scanning, and production compilation before it can be merged.

The workflow configuration is defined in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).

---

## 2. Workflow Specification and Triggers

```yaml
name: CI Pipeline

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}

defaults:
  run:
    shell: bash
```

### Trigger Breakdown
- Pushes to `main`: Runs full regression testing on code entering the primary branch.
- Pull Requests to `main`: Validates proposed changes before merge approval.
- `workflow_dispatch`: Enables manual on-demand pipeline execution from the GitHub Actions console.
- Concurrency Cancellation: If new commits are pushed to an open pull request while a workflow is currently executing, the superseded run is automatically cancelled to save CI resources, while runs on `main` always complete.

---

## 3. Security Hardening and Least Privilege

The CI pipeline is architected to minimize attack surface and prevent credential leakage:
- **`permissions: contents: read`**: Restricts the runner's default `GITHUB_TOKEN` to read-only access. The runner cannot write to the repository, create tags, or alter releases.
- **Zero Secrets Required in CI**: The pipeline does not require or consume live production credentials, Supabase database URLs, or Razorpay private keys. All tests execute using isolated in-process mock providers and test database configurations.
- **Strict Exit Codes**: All commands run with `set -eo pipefail` by default. Any failure in a subshell or command pipeline causes immediate workflow termination.
- **No Artifact Leakage**: No `.env` files, build caches, or temporary database files are uploaded as build artifacts.

---

## 4. Pipeline Jobs Breakdown

```
                  +-------------------------------+
                  |       WORKFLOW TRIGGER        |
                  +---------------+---------------+
                                  |
            +---------------------+---------------------+
            |                                           |
            v                                           v
+-------------------------------+   +-------------------------------+
|  Job 1: backend-tests         |   |  Job 2: frontend-build        |
|  - Runner: Ubuntu Latest      |   |  - Runner: Ubuntu Latest      |
|  - Runtime: Python 3.12       |   |  - Runtime: Node.js 20        |
|  - Cache: pip dependencies    |   |  - Cache: npm dependencies    |
|                               |   |                               |
|  1. actions/checkout@v4       |   |  1. actions/checkout@v4       |
|  2. Set up Python 3.12        |   |  2. Set up Node.js 20         |
|  3. pip install requirements  |   |  3. npm ci                    |
|  4. Run pytest -v (391 tests) |   |  4. npm test (94 tests)       |
|  5. Repository secret scan    |   |  5. npm run build             |
+-------------------------------+   +-------------------------------+
            |                                           |
            +---------------------+---------------------+
                                  |
                                  v
                  +-------------------------------+
                  |       PIPELINE STATUS         |
                  |  Pass: All Quality Gates OK   |
                  |  Fail: Blocks Merge on Error  |
                  +-------------------------------+
```

### 4.1 Job 1: `backend-tests`
- Operating System: `ubuntu-latest`
- Python Version: `3.12`
- Dependency Caching: Caches `~/.cache/pip` keyed against `backend/requirements.txt`.
- Execution Steps:
  1. Check out repository code via `actions/checkout@v4`.
  2. Set up Python 3.12 via `actions/setup-python@v5`.
  3. Upgrade pip and install locked backend dependencies: `pip install -r backend/requirements.txt`.
  4. Execute full backend pytest suite in isolated test mode:
     ```bash
     pytest -v
     ```
     Configured environment variables:
     - `ENVIRONMENT=test`
     - `DATABASE_URL=sqlite:///./ci_test.db`
     - `AI_PROVIDER=mock`
     - `PYTHONUNBUFFERED=1`
     - `PYTHONDONTWRITEBYTECODE=1`
  5. Runs all 391 tests, including adversarial security checks and the repository-wide secret leak prevention scanner.

### 4.2 Job 2: `frontend-build`
- Operating System: `ubuntu-latest`
- Node.js Version: `20`
- Dependency Caching: Caches `~/.npm` keyed against `frontend/package-lock.json`.
- Execution Steps:
  1. Check out repository code via `actions/checkout@v4`.
  2. Set up Node.js 20 via `actions/setup-node@v4`.
  3. Clean install locked dependencies: `npm ci` in `frontend/`.
  4. Run automated frontend test runner: `npm test` (verifying API client, auth helpers, and UI component contracts).
  5. Run Next.js production build:
     ```bash
     npm run build
     ```
     Configured environment variables:
     - `CI=true`
     - `NEXT_TELEMETRY_DISABLED=1`
     - `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`

---

## 5. Failure Propagation and Diagnostics

- Independent Job Execution: `backend-tests` and `frontend-build` run in parallel. A failure in one job reports distinctly in the GitHub Actions UI, allowing developers to isolate backend vs frontend regressions immediately.
- Strict Failure Policy: The pipeline does not utilize `continue-on-error: true`. Any test failure, TypeScript compilation error, or lint violation fails the entire workflow.
- Troubleshooting Failures:
  - Backend Failure: Reproduce locally via `cd backend && pytest tests/ -v`.
  - Frontend Test Failure: Reproduce locally via `cd frontend && npm test`.
  - Frontend Build Failure: Reproduce locally via `cd frontend && npm ci && npm run build`.
