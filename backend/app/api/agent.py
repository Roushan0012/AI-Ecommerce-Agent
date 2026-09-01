from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.agent import (
    AgentRecommendRequest,
    AgentRecommendResponse,
    AgentSearchRequest,
    AgentSearchResponse,
    AgentUnderstandRequest,
    AgentUnderstandResponse,
)
from app.schemas.growth import (
    AgentGrowthRequest,
    AgentGrowthResponse,
)
from app.services.agent_guardrails import agent_guardrail_service
from app.services.ai_agent import (
    AIConfigurationError,
    AIProviderError,
    ai_agent_service,
)
from app.services.audit_service import audit_service
from app.services.growth_service import growth_service
from app.services.product_service import product_service
from app.services.recommendation_service import recommendation_service

router = APIRouter(prefix="/api/agent", tags=["AI Agent"])


@router.post("/understand", response_model=AgentUnderstandResponse)
async def understand_intent(
    request: AgentUnderstandRequest,
    db: Session = Depends(get_db),
):
    """
    Analyzes natural-language shopping messages and returns structured intent.
    Converts phrases like 'wireless headphones under ₹5000' into structured query parameters.
    """
    try:
        clean_prompt = agent_guardrail_service.sanitize_user_prompt(request.message)
        audit_service.record_event(
            db=db,
            event_type="USER_REQUEST",
            action="understand_intent",
            payload={"message": clean_prompt},
            status="success",
        )

        response = await ai_agent_service.understand_user_message(clean_prompt)
        response.intent = agent_guardrail_service.validate_shopping_intent(response.intent)
        response.message = agent_guardrail_service.redact_sensitive_information(response.message)

        audit_service.record_event(
            db=db,
            event_type="INTENT_DETECTED",
            action="understand_intent",
            payload={"message": clean_prompt},
            result=response.intent.model_dump() if hasattr(response.intent, "model_dump") else response.intent.dict(),
            status="success",
        )

        return response
    except AIConfigurationError as e:
        audit_service.record_event(
            db=db,
            event_type="ERROR",
            action="understand_intent",
            error_message=str(e),
            status="failed",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except AIProviderError as e:
        audit_service.record_event(
            db=db,
            event_type="ERROR",
            action="understand_intent",
            error_message=str(e),
            status="failed",
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )
    except Exception as exc:
        audit_service.record_event(
            db=db,
            event_type="ERROR",
            action="understand_intent",
            error_message=str(exc),
            status="failed",
        )
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
        clean_prompt = agent_guardrail_service.sanitize_user_prompt(request.message)
        audit_service.record_event(
            db=db,
            event_type="USER_REQUEST",
            action="agent_search",
            payload={"message": clean_prompt, "page": request.page, "page_size": request.page_size},
            status="success",
        )

        understand_res = await ai_agent_service.understand_user_message(clean_prompt)
        intent = agent_guardrail_service.validate_shopping_intent(understand_res.intent)

        # If non-shopping intent, return without querying database
        if intent.intent != "product_search":
            return AgentSearchResponse(
                message=agent_guardrail_service.redact_sensitive_information(understand_res.message),
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
            summary_message = f"No products found matching '{clean_prompt}'."
        else:
            summary_message = f"Found {products_res.total} product(s) matching your request."

        audit_service.record_event(
            db=db,
            event_type="TOOL_RESULT",
            action="product_search",
            payload={"search_query": intent.search_query, "category": intent.category},
            result={"total_matches": products_res.total},
            status="success",
        )

        return AgentSearchResponse(
            message=agent_guardrail_service.redact_sensitive_information(summary_message),
            intent=intent,
            items=products_res.items,
            total=products_res.total,
            page=products_res.page,
            page_size=products_res.page_size,
        )
    except AIConfigurationError as e:
        audit_service.record_event(
            db=db, event_type="ERROR", action="agent_search", error_message=str(e), status="failed"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except AIProviderError as e:
        audit_service.record_event(
            db=db, event_type="ERROR", action="agent_search", error_message=str(e), status="failed"
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )
    except Exception as exc:
        audit_service.record_event(
            db=db, event_type="ERROR", action="agent_search", error_message=str(exc), status="failed"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while searching products with the AI agent.",
        )


@router.post("/recommend", response_model=AgentRecommendResponse)
async def recommend_products_with_agent(
    request: AgentRecommendRequest,
    db: Session = Depends(get_db),
):
    """
    End-to-end AI product recommendation:
    1. Understands customer natural language shopping intent.
    2. Retrieves product candidates from Supabase PostgreSQL database.
    3. Scores and ranks candidates using multi-factor deterministic scoring.
    4. Returns ranked product recommendations with scores and explainability reasons.
    """
    try:
        clean_prompt = agent_guardrail_service.sanitize_user_prompt(request.message)
        audit_service.record_event(
            db=db,
            event_type="USER_REQUEST",
            action="agent_recommend",
            payload={"message": clean_prompt},
            status="success",
        )

        understand_res = await ai_agent_service.understand_user_message(clean_prompt)
        intent = agent_guardrail_service.validate_shopping_intent(understand_res.intent)

        # If non-shopping intent, return conversational response without database search
        if intent.intent != "product_search":
            return AgentRecommendResponse(
                message=agent_guardrail_service.redact_sensitive_information(understand_res.message),
                intent=intent,
                items=[],
                total=0,
                page=request.page,
                page_size=request.page_size,
            )

        # Score, rank, and recommend products
        recommended_items, total = recommendation_service.recommend_products(
            db=db,
            intent=intent,
            user_message=clean_prompt,
            page=request.page,
            page_size=request.page_size,
        )

        if total == 0:
            summary_message = f"No recommended products found matching '{clean_prompt}'."
        else:
            summary_message = f"Found {total} top recommendation(s) for your request."

        audit_service.record_event(
            db=db,
            event_type="RECOMMENDATION",
            action="recommend_products",
            payload={"query": clean_prompt, "intent": intent.model_dump() if hasattr(intent, "model_dump") else intent.dict()},
            result={"recommendation_count": total},
            status="success",
        )

        return AgentRecommendResponse(
            message=agent_guardrail_service.redact_sensitive_information(summary_message),
            intent=intent,
            items=recommended_items,
            total=total,
            page=request.page,
            page_size=request.page_size,
        )
    except AIConfigurationError as e:
        audit_service.record_event(
            db=db, event_type="ERROR", action="agent_recommend", error_message=str(e), status="failed"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except AIProviderError as e:
        audit_service.record_event(
            db=db, event_type="ERROR", action="agent_recommend", error_message=str(e), status="failed"
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )
    except Exception as exc:
        audit_service.record_event(
            db=db, event_type="ERROR", action="agent_recommend", error_message=str(exc), status="failed"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating recommendations with the AI agent.",
        )


@router.post("/growth", response_model=AgentGrowthResponse)
async def generate_growth_opportunities(
    request: AgentGrowthRequest,
    db: Session = Depends(get_db),
):
    """
    AI Growth Engine: generates Upsell and Cross-sell opportunities:
    1. Understands customer natural language shopping intent.
    2. Identifies matching primary products.
    3. Generates ranked upsell alternatives (specification improvements within budget).
    4. Generates ranked cross-sell accessory companions.
    """
    try:
        clean_prompt = agent_guardrail_service.sanitize_user_prompt(request.message)
        audit_service.record_event(
            db=db,
            event_type="USER_REQUEST",
            action="agent_growth",
            payload={"message": clean_prompt},
            status="success",
        )

        understand_res = await ai_agent_service.understand_user_message(clean_prompt)
        intent = agent_guardrail_service.validate_shopping_intent(understand_res.intent)

        # If non-shopping intent, return conversational response without growth items
        if intent.intent != "product_search":
            return AgentGrowthResponse(
                message=agent_guardrail_service.redact_sensitive_information(understand_res.message),
                intent=intent,
                primary_products=[],
                upsell=[],
                cross_sell=[],
                total=0,
                page=request.page,
                page_size=request.page_size,
            )

        # Generate growth opportunities
        primary_products, upsell_items, cross_sell_items, total = (
            growth_service.generate_growth_recommendations(
                db=db,
                intent=intent,
                user_message=clean_prompt,
                page=request.page,
                page_size=request.page_size,
            )
        )

        if total == 0 and not primary_products:
            summary_message = f"No growth recommendations found for '{clean_prompt}'."
        else:
            summary_message = (
                f"I found suitable products and {total} useful upgrade and accessory options."
            )

        audit_service.record_event(
            db=db,
            event_type="RECOMMENDATION",
            action="growth_recommendations",
            payload={"query": clean_prompt},
            result={"upsells_count": len(upsell_items), "cross_sells_count": len(cross_sell_items)},
            status="success",
        )

        return AgentGrowthResponse(
            message=agent_guardrail_service.redact_sensitive_information(summary_message),
            intent=intent,
            primary_products=primary_products,
            upsell=upsell_items,
            cross_sell=cross_sell_items,
            total=total,
            page=request.page,
            page_size=request.page_size,
        )
    except AIConfigurationError as e:
        audit_service.record_event(
            db=db, event_type="ERROR", action="agent_growth", error_message=str(e), status="failed"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except AIProviderError as e:
        audit_service.record_event(
            db=db, event_type="ERROR", action="agent_growth", error_message=str(e), status="failed"
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )
    except Exception as exc:
        audit_service.record_event(
            db=db, event_type="ERROR", action="agent_growth", error_message=str(exc), status="failed"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating upsell and cross-sell recommendations.",
        )
