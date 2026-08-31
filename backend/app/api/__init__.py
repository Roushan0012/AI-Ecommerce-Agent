from app.api.agent import router as agent_router
from app.api.products import router as products_router

__all__ = [
    "products_router",
    "agent_router",
]
