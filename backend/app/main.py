import json
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.api.admin import router as admin_router
from app.api.agent import router as agent_router
from app.api.agent_commerce import router as agent_commerce_router
from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.cart import router as cart_router
from app.api.dashboard import router as dashboard_router
from app.api.orders import router as orders_router
from app.api.payments import router as payments_router
from app.api.products import router as products_router
from app.core.config import settings, ConfigurationError
from app.core.database import check_database_connection
from app.core.logging_security import setup_security_logging, redact_sensitive_text
from app.core.security_middleware import (
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
    RateLimitMiddleware,
)

logger = logging.getLogger("app.main")
setup_security_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_security_logging()
    if settings.is_production:
        settings.validate_production_config()
    yield


app = FastAPI(
    title="AI Commerce Agent API",
    description="Backend API for Razorpay AI Buildathon Track 01 - AI Commerce Agent",
    version="0.1.0",
    docs_url="/docs" if (not settings.is_production or os.getenv("ENABLE_DOCS", "false").lower() == "true") else None,
    redoc_url="/redoc" if (not settings.is_production or os.getenv("ENABLE_DOCS", "false").lower() == "true") else None,
    openapi_url="/openapi.json" if (not settings.is_production or os.getenv("ENABLE_DOCS", "false").lower() == "true") else None,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# 1. Security Headers (applies to all HTTP responses)
app.add_middleware(SecurityHeadersMiddleware)

# 2. CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.validate_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Request Size Limiting (blocks oversized request bodies)
app.add_middleware(RequestSizeLimitMiddleware)

# 4. Rate Limiting (blocks brute-force and request flooding)
app.add_middleware(RateLimitMiddleware)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Delegate to FastAPI's built-in encoder, then redact sensitive fields (passwords, tokens, keys)
    res = await request_validation_exception_handler(request, exc)
    try:
        data = json.loads(res.body.decode("utf-8"))
        if isinstance(data, dict) and "detail" in data and isinstance(data["detail"], list):
            for err in data["detail"]:
                if isinstance(err, dict):
                    loc = [str(part).lower() for part in err.get("loc", ())]
                    is_sensitive = any(
                        s in loc for s in ("password", "secret", "token", "key", "authorization", "agent_key")
                    )
                    if is_sensitive and "input" in err:
                        err["input"] = "[REDACTED]"
                    if is_sensitive and "ctx" in err and isinstance(err["ctx"], dict):
                        for k in list(err["ctx"].keys()):
                            if any(s in str(k).lower() for s in ("password", "secret", "token", "key")):
                                err["ctx"][k] = "[REDACTED]"
        return JSONResponse(
            status_code=res.status_code,
            content=data,
            headers=dict(res.headers),
        )
    except Exception:
        return res


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    sanitized_msg = redact_sensitive_text(str(exc))
    logger.error(
        f"Unhandled server error on {request.method} {request.url.path}: {sanitized_msg}",
        exc_info=settings.DEBUG,
    )
    if settings.is_production:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred. Please contact support."},
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": sanitized_msg},
    )

# Include API Routers
app.include_router(products_router)
app.include_router(agent_router)
app.include_router(cart_router)
app.include_router(orders_router)
app.include_router(payments_router)
app.include_router(audit_router)
app.include_router(dashboard_router)
app.include_router(admin_router)
app.include_router(agent_commerce_router)
app.include_router(auth_router)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "ai-commerce-agent-api",
    }


@app.get("/api/health/database")
def database_health_check():
    try:
        is_connected = check_database_connection()
        if not is_connected:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "status": "error",
                    "database": "disconnected",
                    "message": "Database query check failed",
                },
            )
        return {
            "status": "ok",
            "database": "connected",
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "error",
                "database": "disconnected",
                "message": "Database connection failed",
            },
        )
