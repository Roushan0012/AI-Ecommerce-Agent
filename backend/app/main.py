from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
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
from app.core.database import check_database_connection

app = FastAPI(
    title="AI Commerce Agent API",
    description="Backend API for Razorpay AI Buildathon Track 01 - AI Commerce Agent",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
