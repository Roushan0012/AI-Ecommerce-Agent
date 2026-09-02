import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AuditEventType(str, Enum):
    USER_REQUEST = "USER_REQUEST"
    USER_REGISTERED = "USER_REGISTERED"
    USER_LOGIN = "USER_LOGIN"
    INTENT_DETECTED = "INTENT_DETECTED"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"
    RECOMMENDATION = "RECOMMENDATION"
    CART_UPDATED = "CART_UPDATED"
    ORDER_CREATED = "ORDER_CREATED"
    PAYMENT_EVENT = "PAYMENT_EVENT"
    SECURITY_VIOLATION = "SECURITY_VIOLATION"
    ERROR = "ERROR"


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: Optional[uuid.UUID] = None
    session_id: Optional[str] = None
    event_type: str
    action: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    status: str
    error_message: Optional[str] = None
    cart_id: Optional[uuid.UUID] = None
    order_id: Optional[uuid.UUID] = None
    payment_id: Optional[uuid.UUID] = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int = Field(..., ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1)
