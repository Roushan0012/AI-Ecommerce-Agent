# ==============================================================================
# AI Commerce Agent - Production Backend Dockerfile (Phase 18F-2)
# ==============================================================================

FROM python:3.12-slim

WORKDIR /app

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    WEB_CONCURRENCY=4

# Install runtime dependencies (curl for health check probe)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source code
COPY app ./app

# Add and run as dedicated non-root user
RUN useradd -m -u 1001 -s /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Container liveness health check probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Production ASGI server entry point
CMD ["sh", "-c", "uvicorn app.main:app --host ${HOST} --port ${PORT} --workers ${WEB_CONCURRENCY} --proxy-headers --forwarded-allow-ips '*'"]
