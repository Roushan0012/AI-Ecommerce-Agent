from fastapi import FastAPI

app = FastAPI(
    title="AI Commerce Agent API",
    description="Backend API for Razorpay AI Buildathon Track 01 - AI Commerce Agent",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "ai-commerce-agent-api",
    }
