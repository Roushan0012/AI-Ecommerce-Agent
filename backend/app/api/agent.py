from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.agent import (
    AgentSearchRequest,
    AgentSearchResponse,
    AgentUnderstandRequest,
    AgentUnderstandResponse,
)
from app.services.ai_agent import (
    AIConfigurationError,
    AIProviderError,
    ai_agent_service,
)
from app.services.product_service import product_service

router = APIRouter(prefix="/api/agent", tags=["AI Agent"])


@router.post("/understand", response_model=AgentUnderstandResponse)
async def understand_intent(request: AgentUnderstandRequest):
    """
    Analyzes natural-language shopping messages and returns structured intent.
    Converts phrases like 'wireless headphones under ₹5000' into structured query parameters.
    """
    try:
        response = await ai_agent_service.understand_user_message(request.message)
        return response
    except AIConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except AIProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request with the AI agent.",
        )


@router.post("/search", response_model=AgentSearchResponse)
async def search_products_with_agent(
    request: AgentSearchRequest,
    db: Session = Depends(get_db),
):
    """
    End-to-end agent product discovery:
    1. Understands customer natural language query into ShoppingIntent.
    2. Translates intent into catalog filters (keyword, category, price bounds, availability).
    3. Queries Supabase database and returns matching products with pagination.
    """
    try:
        understand_res = await ai_agent_service.understand_user_message(request.message)
        intent = understand_res.intent

        # If non-shopping intent, return without querying database
        if intent.intent != "product_search":
            return AgentSearchResponse(
                message=understand_res.message,
                intent=intent,
                items=[],
                total=0,
                page=request.page,
                page_size=request.page_size,
            )

        # Query catalog using translated shopping intent filters
        products_res = product_service.list_products(
            db=db,
            search=intent.search_query,
            category=intent.category,
            min_price=intent.min_price,
            max_price=intent.max_price,
            available=intent.availability_required,
            page=request.page,
            page_size=request.page_size,
        )

        if products_res.total == 0:
            summary_message = f"No products found matching '{request.message}'."
        else:
            summary_message = f"Found {products_res.total} product(s) matching your request."

        return AgentSearchResponse(
            message=summary_message,
            intent=intent,
            items=products_res.items,
            total=products_res.total,
            page=products_res.page,
            page_size=products_res.page_size,
        )
    except AIConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except AIProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while searching products with the AI agent.",
        )
