from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.dashboard import (
    DashboardActivityResponse,
    DashboardOrdersResponse,
    OverviewMetricsResponse,
)
from app.services.dashboard_service import dashboard_service

router = APIRouter(prefix="/api/dashboard", tags=["Merchant Dashboard"])


@router.get(
    "/overview",
    response_model=OverviewMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Merchant Dashboard Overview Metrics",
)
def get_dashboard_overview(
    db: Session = Depends(get_db),
):
    """
    Returns authoritative backend-derived commerce metrics:
    - Total Revenue & Paid Orders
    - Average Order Value & Cart Conversion Rate
    - AI-Assisted Order Counts & Revenue Attribution
    - Recommendation, Upsell, and Cross-sell Performance
    """
    return dashboard_service.get_overview_metrics(db=db)


@router.get(
    "/orders",
    response_model=DashboardOrdersResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Recent Merchant Orders",
)
def get_dashboard_orders(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Number of orders per page"),
    db: Session = Depends(get_db),
):
    """
    Returns recent merchant orders with live payment statuses and AI-assisted attribution flags.
    """
    return dashboard_service.get_recent_orders(
        db=db,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/activity",
    response_model=DashboardActivityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Recent Agent Activity Feed",
)
def get_dashboard_activity(
    limit: int = Query(10, ge=1, le=50, description="Max activities to return"),
    db: Session = Depends(get_db),
):
    """
    Returns recent observable agent interactions, commerce actions, and security events.
    """
    return dashboard_service.get_recent_activity(
        db=db,
        limit=limit,
    )
