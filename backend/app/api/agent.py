from fastapi import APIRouter, HTTPException, status
from app.schemas.agent import AgentUnderstandRequest, AgentUnderstandResponse
from app.services.ai_agent import (
    AIConfigurationError,
    AIProviderError,
    ai_agent_service,
)

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
