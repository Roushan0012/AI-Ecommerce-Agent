"""HTTP Security Middlewares (Phase 18C).

Implements:
1. SecurityHeadersMiddleware: Adds X-Content-Type-Options, X-Frame-Options, X-XSS-Protection,
   Referrer-Policy, Permissions-Policy, and production HSTS.
2. RequestSizeLimitMiddleware: Rejects requests exceeding MAX_REQUEST_BODY_BYTES with HTTP 413.
3. RateLimitMiddleware: Sliding-window rate limiting for authentication and general API endpoints.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.core.rate_limit import get_client_ip, rate_limiter


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects defensive HTTP security headers into all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if settings.SECURITY_HEADERS_ENABLED:
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
            if settings.is_production:
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Enforces maximum allowed request payload size."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > settings.MAX_REQUEST_BODY_BYTES:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": f"Request payload exceeds maximum allowed size of {settings.MAX_REQUEST_BODY_BYTES} bytes."},
                    )
            except ValueError:
                pass
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforces sliding-window rate limiting per client IP."""

    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        path = request.url.path

        # Whitelist non-abusable system endpoints
        if path in ("/api/health", "/api/health/database", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        client_ip = get_client_ip(request)

        # 1. Authentication Tier (Login / Registration)
        if path.startswith("/api/auth/login") or path.startswith("/api/auth/register"):
            limit = settings.RATE_LIMIT_AUTH_PER_MINUTE
            key = f"auth:{client_ip}"
        # 2. General API Tier
        elif path.startswith("/api/"):
            limit = settings.RATE_LIMIT_DEFAULT_PER_MINUTE
            key = f"default:{client_ip}"
        else:
            return await call_next(request)

        allowed, count, retry_after = rate_limiter.is_allowed(key, max_requests=limit, window_seconds=60)
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Please retry in a few moments."},
                headers={"Retry-After": str(int(retry_after))},
            )

        return await call_next(request)
