import json
import uuid
from typing import Optional
import pytest
from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.main import app
from app.models.user import User
from app.services.ai_agent import MockAIProvider, ai_agent_service


@pytest.fixture(autouse=True)
def set_mock_ai_provider_for_tests():
    """Ensure all automated tests use deterministic MockAIProvider."""
    prev_provider = ai_agent_service._provider
    ai_agent_service._provider = MockAIProvider()
    yield
    ai_agent_service._provider = prev_provider


@pytest.fixture(autouse=True)
def handle_test_auth_dependencies(request):
    """
    Ensures Phase 17 tests execute strict real JWT validation and role checks
    while legacy Phase 1-16 test suites seamlessly resolve active test users.
    """
    # If this is a Phase 17 JWT auth, role, or A2A boundary test, ensure NO dependency override is present
    if any(k in request.node.nodeid for k in ["test_jwt_protected", "test_auth", "test_role", "test_authorization", "test_a2a"]):
        app.dependency_overrides.pop(get_current_user, None)
        yield
        app.dependency_overrides.pop(get_current_user, None)
        return

    # For legacy test suites from Phases 1-16:
    async def legacy_get_current_user_with_db(
        request: Request,
        authorization: Optional[str] = Header(None, alias="Authorization"),
        db: Session = Depends(get_db),
    ) -> User:
        if authorization:
            return get_current_user(authorization=authorization, db=db)

        target_uuid = None

        # 1. Check path parameters
        path_cust = request.path_params.get("customer_id")
        if path_cust:
            try:
                target_uuid = uuid.UUID(str(path_cust))
            except Exception:
                pass

        # 2. Check JSON body if no path param
        if not target_uuid:
            try:
                body_bytes = await request.body()
                if body_bytes:
                    body_json = json.loads(body_bytes.decode("utf-8"))
                    if isinstance(body_json, dict):
                        if "customer_id" in body_json and body_json["customer_id"]:
                            target_uuid = uuid.UUID(str(body_json["customer_id"]))
                        elif "order_id" in body_json and body_json["order_id"]:
                            from app.models.order import Order
                            try:
                                o_uuid = uuid.UUID(str(body_json["order_id"]))
                                ord_record = db.query(Order).filter(Order.id == o_uuid).first()
                                if ord_record and ord_record.customer_id:
                                    target_uuid = ord_record.customer_id
                            except Exception:
                                pass
            except Exception:
                pass

        # 3. Fallback default test UUID
        if not target_uuid:
            target_uuid = uuid.UUID("c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c")

        user = db.query(User).filter(User.id == target_uuid).first()
        if not user:
            user = User(
                id=target_uuid,
                email=f"user_{target_uuid}@test.local",
                password_hash="$argon2id$v=19$m=65536,t=3,p=4$mock$hash",
                role="merchant",
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        elif user.role != "merchant" and (request.url.path.startswith("/api/dashboard") or request.url.path.startswith("/api/admin")):
            user.role = "merchant"
            db.commit()
            db.refresh(user)
        return user

    app.dependency_overrides[get_current_user] = legacy_get_current_user_with_db
    yield
    app.dependency_overrides.pop(get_current_user, None)
