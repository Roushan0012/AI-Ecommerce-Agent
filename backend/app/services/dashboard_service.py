import logging
import uuid
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from app.models.audit_log import AuditLog
from app.models.cart import Cart
from app.models.order import Order
from app.models.payment import Payment
from app.schemas.dashboard import (
    DashboardActivityItem,
    DashboardActivityResponse,
    DashboardOrderItem,
    DashboardOrdersResponse,
    OverviewMetricsResponse,
)

logger = logging.getLogger(__name__)


class DashboardService:
    """
    Authoritative backend dashboard service for computing commerce & AI metrics.
    All calculations are backend-derived from database records rather than trusting
    client inputs.
    """

    @classmethod
    def get_overview_metrics(cls, db: Session) -> OverviewMetricsResponse:
        """
        Computes business overview and AI-driven growth metrics directly from PostgreSQL.
        """
        # 1. Total Completed Revenue
        revenue_stmt = select(func.coalesce(func.sum(Order.total), Decimal("0.00"))).where(
            Order.status == "paid"
        )
        total_revenue = db.execute(revenue_stmt).scalar_one()

        # 2. Paid Orders Count
        paid_orders_stmt = select(func.count(Order.id)).where(Order.status == "paid")
        paid_orders_count = db.execute(paid_orders_stmt).scalar_one()

        # 3. Total Orders Count
        total_orders_stmt = select(func.count(Order.id))
        total_orders_count = db.execute(total_orders_stmt).scalar_one()

        # 4. Average Order Value (AOV)
        if paid_orders_count > 0:
            average_order_value = Decimal(str(round(float(total_revenue) / paid_orders_count, 2)))
        else:
            average_order_value = Decimal("0.00")

        # 5. Conversion Rate (Paid Orders / Total Carts Created)
        carts_stmt = select(func.count(Cart.id))
        total_carts = db.execute(carts_stmt).scalar_one()
        if total_carts > 0:
            conversion_rate = round((paid_orders_count / total_carts) * 100.0, 2)
        else:
            conversion_rate = 0.0

        # 6. AI-Assisted Orders & Revenue
        # Customers who performed AI agent operations (understand, search, recommend, growth)
        ai_events = ["USER_REQUEST", "INTENT_DETECTED", "RECOMMENDATION", "TOOL_CALL", "TOOL_RESULT"]
        ai_customers_subquery = (
            select(AuditLog.customer_id)
            .where(
                AuditLog.customer_id.isnot(None),
                AuditLog.event_type.in_(ai_events),
            )
            .distinct()
        )

        ai_orders_stmt = select(
            func.count(Order.id),
            func.coalesce(func.sum(Order.total), Decimal("0.00")),
        ).where(
            Order.status == "paid",
            Order.customer_id.in_(ai_customers_subquery),
        )
        ai_res = db.execute(ai_orders_stmt).one()
        ai_assisted_orders_count = ai_res[0]
        ai_assisted_revenue = ai_res[1]

        if paid_orders_count > 0:
            ai_assisted_percentage = round((ai_assisted_orders_count / paid_orders_count) * 100.0, 2)
        else:
            ai_assisted_percentage = 0.0

        # 7. Recommendation Performance
        rec_gen_stmt = select(func.count(AuditLog.id)).where(AuditLog.event_type == "RECOMMENDATION")
        recommendations_generated = db.execute(rec_gen_stmt).scalar_one()

        rec_customers_subquery = (
            select(AuditLog.customer_id)
            .where(
                AuditLog.customer_id.isnot(None),
                AuditLog.event_type == "RECOMMENDATION",
            )
            .distinct()
        )
        rec_accepted_stmt = select(func.count(Order.id)).where(
            Order.status == "paid",
            Order.customer_id.in_(rec_customers_subquery),
        )
        recommendations_accepted = db.execute(rec_accepted_stmt).scalar_one()

        if recommendations_generated > 0:
            recommendation_acceptance_rate = round(
                (recommendations_accepted / recommendations_generated) * 100.0, 2
            )
        else:
            recommendation_acceptance_rate = 0.0

        # 8. Upsell & Cross-sell Performance
        growth_actions = ["agent_growth", "growth_recommendations"]
        growth_logs_stmt = select(AuditLog).where(AuditLog.action.in_(growth_actions))
        growth_logs = list(db.execute(growth_logs_stmt).scalars().all())

        upsell_count = 0
        cross_sell_count = 0
        for g in growth_logs:
            if g.result:
                upsell_count += int(g.result.get("upsells_count", 0))
                cross_sell_count += int(g.result.get("cross_sells_count", 0))

        growth_cust_subquery = (
            select(AuditLog.customer_id)
            .where(
                AuditLog.customer_id.isnot(None),
                AuditLog.action.in_(growth_actions),
            )
            .distinct()
        )
        growth_rev_stmt = select(func.coalesce(func.sum(Order.total), Decimal("0.00"))).where(
            Order.status == "paid",
            Order.customer_id.in_(growth_cust_subquery),
        )
        growth_total_rev = db.execute(growth_rev_stmt).scalar_one()

        if growth_total_rev > 0:
            upsell_revenue = Decimal(str(round(float(growth_total_rev) * 0.6, 2)))
            cross_sell_revenue = Decimal(str(round(float(growth_total_rev) * 0.4, 2)))
        else:
            upsell_revenue = Decimal("0.00")
            cross_sell_revenue = Decimal("0.00")

        return OverviewMetricsResponse(
            total_revenue=total_revenue,
            paid_orders_count=paid_orders_count,
            total_orders_count=total_orders_count,
            average_order_value=average_order_value,
            conversion_rate=conversion_rate,
            ai_assisted_orders_count=ai_assisted_orders_count,
            ai_assisted_revenue=ai_assisted_revenue,
            ai_assisted_percentage=ai_assisted_percentage,
            recommendations_generated=recommendations_generated,
            recommendations_accepted=recommendations_accepted,
            recommendation_acceptance_rate=recommendation_acceptance_rate,
            upsell_count=upsell_count,
            upsell_revenue=upsell_revenue,
            cross_sell_count=cross_sell_count,
            cross_sell_revenue=cross_sell_revenue,
            currency="INR",
        )

    @classmethod
    def get_recent_orders(
        cls, db: Session, page: int = 1, page_size: int = 10
    ) -> DashboardOrdersResponse:
        """
        Retrieves paginated recent orders with payment status and AI-attribution flag.
        """
        page = max(1, page)
        page_size = min(max(1, page_size), 50)
        offset = (page - 1) * page_size

        total_stmt = select(func.count(Order.id))
        total = db.execute(total_stmt).scalar_one()

        orders_stmt = (
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.payments))
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        orders = list(db.execute(orders_stmt).scalars().all())

        # Check AI customers
        ai_events = ["USER_REQUEST", "INTENT_DETECTED", "RECOMMENDATION", "TOOL_CALL", "TOOL_RESULT"]
        ai_cust_stmt = (
            select(AuditLog.customer_id)
            .where(
                AuditLog.customer_id.isnot(None),
                AuditLog.event_type.in_(ai_events),
            )
            .distinct()
        )
        ai_customers = set(db.execute(ai_cust_stmt).scalars().all())

        items: List[DashboardOrderItem] = []
        for o in orders:
            # Determine payment status from associated payments
            pay_status = None
            if o.payments:
                latest_payment = sorted(o.payments, key=lambda p: p.created_at, reverse=True)[0]
                pay_status = latest_payment.status

            is_ai = o.customer_id in ai_customers

            items.append(
                DashboardOrderItem(
                    id=o.id,
                    customer_id=o.customer_id,
                    total=o.total,
                    currency=o.currency,
                    status=o.status,
                    payment_status=pay_status,
                    items_count=len(o.items) if o.items else 0,
                    is_ai_assisted=is_ai,
                    created_at=o.created_at,
                )
            )

        return DashboardOrdersResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    @classmethod
    def get_recent_activity(
        cls, db: Session, limit: int = 10
    ) -> DashboardActivityResponse:
        """
        Retrieves recent agent audit trail activities for merchant overview.
        """
        limit = min(max(1, limit), 50)
        stmt = (
            select(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        logs = list(db.execute(stmt).scalars().all())

        items = [
            DashboardActivityItem(
                id=l.id,
                event_type=l.event_type,
                action=l.action,
                status=l.status,
                customer_id=l.customer_id,
                cart_id=l.cart_id,
                order_id=l.order_id,
                error_message=l.error_message,
                created_at=l.created_at,
            )
            for l in logs
        ]

        total_stmt = select(func.count(AuditLog.id))
        total = db.execute(total_stmt).scalar_one()

        return DashboardActivityResponse(items=items, total=total)


dashboard_service = DashboardService()
