# Docker Containerization and Deployment Architecture

## 1. Overview

The AI Commerce Agent Platform uses multi-stage containerization to package both the backend API and frontend storefront into minimal, reproducible, non-root container images. Local multi-container orchestration is coordinated via Docker Compose.

The implementation is located across:
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`

> **Scope Note**: This document covers **Local Containerization** and **Production Deployment Readiness**. The repository does not currently deploy automatically to cloud platforms (e.g., AWS, GCP, Azure, or Vercel); cloud deployment would involve pushing these verified images to a container registry and orchestrating them via ECS, Cloud Run, Kubernetes, or equivalent runtime environments.

---

## 2. Containerization Architecture

```
+---------------------------------------------------------------------------------+
|                       DOCKER COMPOSE ORCHESTRATION                              |
|                                                                                 |
|   +---------------------------------------+                                     |
|   | Host Port 3000                        |                                     |
|   +-------------------|-------------------+                                     |
|                       v                                                         |
|   +---------------------------------------+                                     |
|   | FRONTEND CONTAINER (ai_commerce_frontend)                                   |
|   | - Base: node:20-alpine (Multi-stage)  |                                     |
|   | - User: nextjs (UID 1001, non-root)   |                                     |
|   | - Port: 3000                          |                                     |
|   | - Healthcheck: wget http://127.0.0.1:3000/                                  |
|   +-------------------|-------------------+                                     |
|                       | depends_on: service_healthy                             |
|                       v                                                         |
|   +---------------------------------------+   +-----------------------------+   |
|   | BACKEND CONTAINER (ai_commerce_backend)|   | EXTERNALLY MANAGED SERVICES |   |
|   | - Base: python:3.12-slim              |   |                             |   |
|   | - User: appuser (UID 1001, non-root)  |   | Managed PostgreSQL Database |   |
|   | - Port: 8000 (Host: 8000)             |-->| (Hosted on Supabase via SSL)|   |
|   | - Concurrency: 4 workers (Uvicorn)    |   |                             |   |
|   | - Healthcheck: curl /api/health       |   | Razorpay Payment Gateway    |   |
|   +---------------------------------------+   | (REST API & Webhooks)       |   |
|                                               +-----------------------------+   |
+---------------------------------------------------------------------------------+
```

---

## 3. Backend Dockerfile Analysis (`backend/Dockerfile`)

The backend container is constructed from a hardened, minimal image based on `python:3.12-slim`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    WEB_CONCURRENCY=4

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN useradd -m -u 1001 -s /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host ${HOST} --port ${PORT} --workers ${WEB_CONCURRENCY} --proxy-headers --forwarded-allow-ips '*'"]
```

### Key Engineering Decisions
- Unprivileged Non-Root User: Creates `appuser` (UID `1001`) and transfers directory ownership with `chown -R appuser:appuser /app`. The container refuses to run with root permissions.
- Minimal Attack Surface: Installs only `curl` (required for health check probes) and clears `/var/lib/apt/lists/*` to keep the image compact.
- Optimized Caching: `requirements.txt` is copied and installed prior to copying `app/`, ensuring Docker layers are cached when only source code changes.
- Production ASGI Execution: Runs Uvicorn with `--workers 4`, `--proxy-headers`, and `--forwarded-allow-ips '*'` to handle reverse proxy termination safely.

---

## 4. Frontend Dockerfile Analysis (`frontend/Dockerfile`)

The frontend container uses a multi-stage build based on `node:20-alpine`:

### Stage 1: Dependencies (`deps`)
```dockerfile
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
```
Installs locked production and development dependencies needed for compilation.

### Stage 2: Builder (`builder`)
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ARG NEXT_PUBLIC_RAZORPAY_KEY_ID=rzp_test_placeholder
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL} \
    NEXT_PUBLIC_RAZORPAY_KEY_ID=${NEXT_PUBLIC_RAZORPAY_KEY_ID}
RUN npm run build
```
Compiles Next.js standalone pages, optimizes assets, and embeds public build arguments.

### Stage 3: Runner (`runner`)
```dockerfile
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME="0.0.0.0"

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/next.config.ts ./next.config.ts

RUN chown -R nextjs:nodejs /app
USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD wget -qO- http://127.0.0.1:3000/ || exit 1

CMD ["npm", "start", "--", "-p", "3000", "-H", "0.0.0.0"]
```

### Key Engineering Decisions
- Least Privilege: Runs as `nextjs` (UID `1001`) in group `nodejs` (GID `1001`).
- Discarded Build Tools: Compiler tools, caches, and raw source files are discarded in Stage 2. Only `.next`, `public`, and runtime `node_modules` enter the final runner image.
- IPv4 Loopback Health Check: Uses `wget -qO- http://127.0.0.1:3000/` to avoid IPv6 address resolution timeouts inherent to Alpine's musl libc.

---

## 5. Multi-Container Orchestration (`docker-compose.yml`)

The `docker-compose.yml` orchestrates the system on a shared Docker bridge network:

```yaml
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    image: ai-commerce-agent-backend:latest
    container_name: ai_commerce_backend
    restart: unless-stopped
    ports:
      - "${PORT:-8000}:8000"
    env_file:
      - ./backend/.env
    environment:
      - ENVIRONMENT=${ENVIRONMENT:-production}
      - DEBUG=false
      - HOST=0.0.0.0
      - PORT=8000
      - WEB_CONCURRENCY=${WEB_CONCURRENCY:-4}
      - CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:3000,http://127.0.0.1:3000}
      - RATE_LIMIT_ENABLED=${RATE_LIMIT_ENABLED:-true}
      - RATE_LIMIT_AUTH_PER_MINUTE=${RATE_LIMIT_AUTH_PER_MINUTE:-10}
      - RATE_LIMIT_DEFAULT_PER_MINUTE=${RATE_LIMIT_DEFAULT_PER_MINUTE:-120}
      - MAX_REQUEST_BODY_BYTES=${MAX_REQUEST_BODY_BYTES:-2097152}
      - SECURITY_HEADERS_ENABLED=${SECURITY_HEADERS_ENABLED:-true}
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/api/health || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        - NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL:-http://localhost:8000}
        - NEXT_PUBLIC_RAZORPAY_KEY_ID=${NEXT_PUBLIC_RAZORPAY_KEY_ID:-rzp_test_placeholder}
    image: ai-commerce-agent-frontend:latest
    container_name: ai_commerce_frontend
    restart: unless-stopped
    ports:
      - "${FRONTEND_PORT:-3000}:3000"
    environment:
      - NODE_ENV=production
      - PORT=3000
      - HOSTNAME=0.0.0.0
      - NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL:-http://localhost:8000}
      - NEXT_PUBLIC_RAZORPAY_KEY_ID=${NEXT_PUBLIC_RAZORPAY_KEY_ID:-rzp_test_placeholder}
    depends_on:
      backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://127.0.0.1:3000/ || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s
```

### Orchestration Guarantees
1. Service Ordering via Health Probes: `frontend` specifies `depends_on: backend: condition: service_healthy`. The frontend container will not start until the backend container's `/api/health` probe succeeds.
2. Graceful Restarts: Containers specify `restart: unless-stopped`, ensuring automatic recovery in the event of an unhandled crash.
3. Network Isolation: Containers share an internal bridge network, allowing secure inter-container communication without exposing internal ports to the host network unnecessarily.

---

## 6. Docker Operations Quick Reference

### Build and Start Containers
```bash
# Build production images and start in background
docker compose up --build -d
```

### Check Service Status and Health
```bash
docker compose ps
```

### View Aggregated Container Logs
```bash
docker compose logs -f
```

### Stop and Teardown Containers
```bash
docker compose down
```
