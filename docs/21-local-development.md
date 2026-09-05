# Local Development Setup and Operator Guide

## 1. Overview

This guide provides step-by-step instructions for configuring, running, testing, and debugging the AI Commerce Agent Platform in a local development environment.

---

## 2. Prerequisites

Ensure the following tools are installed on your host workstation:
- **Python**: Version 3.12 or newer.
- **Node.js**: Version 20 LTS or newer (with `npm`).
- **PostgreSQL**: Version 15+ (local instance or managed Supabase PostgreSQL project).
- **Docker & Docker Compose**: Optional, recommended for containerized testing.
- **Git**: Version 2.30 or newer.

---

## 3. Option A: Local Native Development

### 3.1 Backend Setup (FastAPI)

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install locked backend dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Configure local environment variables:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and set `DATABASE_URL` to your PostgreSQL instance:
   ```env
   ENVIRONMENT=development
   DEBUG=true
   DATABASE_URL=postgresql://postgres:your_password@localhost:5432/ai_commerce_db
   AI_PROVIDER=mock
   RAZORPAY_KEY_ID=rzp_test_placeholder
   ```

5. Execute database schema migrations:
   ```bash
   alembic upgrade head
   ```

6. Seed the catalog with initial merchandise:
   ```bash
   python -m app.core.seed
   ```

7. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   - API Base URL: `http://127.0.0.1:8000`
   - Interactive OpenAPI Documentation (Swagger UI): `http://127.0.0.1:8000/docs`
   - Health Check Probe: `http://127.0.0.1:8000/api/health`

---

### 3.2 Frontend Setup (Next.js 16)

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Configure local environment variables:
   ```bash
   cp .env.example .env.local
   ```
   Ensure `NEXT_PUBLIC_API_BASE_URL` points to your running FastAPI server:
   ```env
   NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
   NEXT_PUBLIC_RAZORPAY_KEY_ID=rzp_test_placeholder
   ```

4. Start the Next.js development server:
   ```bash
   npm run dev
   ```
   - Storefront URL: `http://localhost:3000`

---

## 4. Option B: Multi-Container Orchestration (Docker Compose)

To build and execute both the backend and frontend in containerized environments matching production:

1. Ensure `.env` is configured in the `backend/` directory:
   ```bash
   cp backend/.env.example backend/.env
   ```

2. Build and launch services using Docker Compose:
   ```bash
   docker compose up --build -d
   ```

3. Verify container health status:
   ```bash
   docker compose ps
   ```
   Expected output:
   ```
   NAME                    IMAGE                              COMMAND                  SERVICE    STATUS
   ai_commerce_backend     ai-commerce-agent-backend:latest   "sh -c 'uvicorn app.…"   backend    Up (healthy)
   ai_commerce_frontend    ai-commerce-agent-frontend:latest  "npm start -- -p 300…"   frontend   Up (healthy)
   ```

4. Tail aggregated service logs:
   ```bash
   docker compose logs -f
   ```

5. Teardown containers:
   ```bash
   docker compose down
   ```

---

## 5. Testing and Quality Assurance Commands

### 5.1 Run Full Backend Test Suite
```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```
Verifies all 391 unit, integration, and security tests.

### 5.2 Run Single Backend Test Module
```bash
# Example: Run adversarial security tests
pytest tests/test_adversarial_security.py -v

# Example: Run A2A commerce tests
pytest tests/test_agent_commerce_api.py -v
```

### 5.3 Run Frontend Automated Tests
```bash
cd frontend
npm test
```
Executes all 94 frontend unit and component tests.

### 5.4 Run Next.js Production Build
```bash
cd frontend
npm run build
```
Validates TypeScript typing, routing, and compilation.

### 5.5 Run Postman / Newman API Collection
```bash
npx newman run docs/postman/AI-Commerce-Agent-API.postman_collection.json
```
Executes 35 requests and 108 automated API assertions.

---

## 6. Troubleshooting Common Issues

### Issue 1: Database Connection Refused
- Symptom: Backend startup fails with `psycopg2.OperationalError: could not connect to server`.
- Resolution: Verify that PostgreSQL is running locally (`pg_isready`) or that your Supabase instance is active and not paused. Ensure `DATABASE_URL` uses `postgresql://` and includes the correct password.

### Issue 2: Port 8000 or 3000 Already in Use
- Symptom: `Error: listen EADDRINUSE: address already in use :::3000` or `Errno 48: Address already in use`.
- Resolution: Identify and kill the conflicting process:
  ```bash
  lsof -ti :8000 | xargs kill -9
  lsof -ti :3000 | xargs kill -9
  ```

### Issue 3: CORS Origin Errors in Browser Console
- Symptom: `Access to fetch has been blocked by CORS policy`.
- Resolution: Ensure `CORS_ORIGINS` in `backend/.env` includes the exact protocol and port of the frontend:
  ```env
  CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
  ```

### Issue 4: Missing or Expired Authentication Token
- Symptom: API requests return `401 Unauthorized`.
- Resolution: Sign out and sign in again via the storefront UI, or clear the `localStorage` token via browser developer tools:
  ```javascript
  localStorage.removeItem("ai_commerce_access_token");
  localStorage.removeItem("ai_commerce_user");
  ```
