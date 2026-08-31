from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.api.agent import router as agent_router
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
