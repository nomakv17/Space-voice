"""Revenue analytics API endpoints."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.call_record import CallRecord, CallStatus
from app.models.user import User
from app.services.seed_calls import reseed_calls, seed_calls

router = APIRouter(prefix="/api/v1/revenue", tags=["revenue"])
logger = structlog.get_logger()

CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: User) -> None:
    """Require superuser access."""
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )


class RevenueSummaryResponse(BaseModel):
    """Revenue summary from actual call records."""

    total_revenue: float
    total_cost: float
    total_profit: float
    profit_margin_pct: float
    total_calls: int
    completed_calls: int
    total_minutes: int
    avg_call_duration_secs: float
    avg_revenue_per_call: float
    unique_users: int


class MonthlyRevenueResponse(BaseModel):
    """Monthly revenue breakdown."""

    year: int
    month: int
    month_name: str
    total_revenue: float
    total_cost: float
    total_profit: float
    total_calls: int
    completed_calls: int
    total_minutes: int
    unique_users: int


class SeedResponse(BaseModel):
    """Response from seeding operations."""

    message: str
    users_created: int | None = None
    calls_created: int | None = None
    total_revenue: float | None = None


@router.get("/summary", response_model=RevenueSummaryResponse)
async def get_revenue_summary(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    year: int | None = Query(None, description="Filter by year"),
    month: int | None = Query(None, ge=1, le=12, description="Filter by month (1-12)"),
) -> RevenueSummaryResponse:
    """Get revenue summary aggregated from call records.

    Calculates total revenue, costs, profit from actual call data.
    Optionally filter by year and/or month.
    """
    require_admin(current_user)

    # Build base query
    query = select(
        func.coalesce(func.sum(CallRecord.revenue_usd), 0).label("total_revenue"),
        func.coalesce(func.sum(CallRecord.cost_usd), 0).label("total_cost"),
        func.count(CallRecord.id).label("total_calls"),
        func.count(CallRecord.id).filter(
            CallRecord.status == CallStatus.COMPLETED.value
        ).label("completed_calls"),
        func.coalesce(func.sum(CallRecord.duration_seconds), 0).label("total_seconds"),
        func.count(func.distinct(CallRecord.user_id)).label("unique_users"),
    )

    # Apply filters
    if year:
        query = query.where(extract("year", CallRecord.started_at) == year)
    if month:
        query = query.where(extract("month", CallRecord.started_at) == month)

    result = await db.execute(query)
    row = result.one()

    total_revenue = float(row.total_revenue or 0)
    total_cost = float(row.total_cost or 0)
    total_profit = total_revenue - total_cost
    total_calls = row.total_calls or 0
    completed_calls = row.completed_calls or 0
    total_seconds = row.total_seconds or 0
    unique_users = row.unique_users or 0

    profit_margin_pct = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    avg_duration = total_seconds / completed_calls if completed_calls > 0 else 0
    avg_revenue = total_revenue / completed_calls if completed_calls > 0 else 0

    return RevenueSummaryResponse(
        total_revenue=round(total_revenue, 2),
        total_cost=round(total_cost, 2),
        total_profit=round(total_profit, 2),
        profit_margin_pct=round(profit_margin_pct, 2),
        total_calls=total_calls,
        completed_calls=completed_calls,
        total_minutes=total_seconds // 60,
        avg_call_duration_secs=round(avg_duration, 1),
        avg_revenue_per_call=round(avg_revenue, 4),
        unique_users=unique_users,
    )


@router.get("/history", response_model=list[MonthlyRevenueResponse])
async def get_revenue_history(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(12, ge=1, le=24, description="Number of months to return"),
) -> list[MonthlyRevenueResponse]:
    """Get monthly revenue history from call records.

    Returns aggregated revenue data per month, sorted by most recent first.
    Only includes months that have actual call data.
    """
    require_admin(current_user)

    # Aggregate by year and month
    query = (
        select(
            extract("year", CallRecord.started_at).label("year"),
            extract("month", CallRecord.started_at).label("month"),
            func.coalesce(func.sum(CallRecord.revenue_usd), 0).label("total_revenue"),
            func.coalesce(func.sum(CallRecord.cost_usd), 0).label("total_cost"),
            func.count(CallRecord.id).label("total_calls"),
            func.count(CallRecord.id).filter(
                CallRecord.status == CallStatus.COMPLETED.value
            ).label("completed_calls"),
            func.coalesce(func.sum(CallRecord.duration_seconds), 0).label("total_seconds"),
            func.count(func.distinct(CallRecord.user_id)).label("unique_users"),
        )
        .group_by(
            extract("year", CallRecord.started_at),
            extract("month", CallRecord.started_at),
        )
        .order_by(
            extract("year", CallRecord.started_at).desc(),
            extract("month", CallRecord.started_at).desc(),
        )
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.fetchall()

    month_names = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]

    history = []
    for row in rows:
        year = int(row.year)
        month = int(row.month)
        total_revenue = float(row.total_revenue or 0)
        total_cost = float(row.total_cost or 0)

        history.append(MonthlyRevenueResponse(
            year=year,
            month=month,
            month_name=month_names[month],
            total_revenue=round(total_revenue, 2),
            total_cost=round(total_cost, 2),
            total_profit=round(total_revenue - total_cost, 2),
            total_calls=row.total_calls or 0,
            completed_calls=row.completed_calls or 0,
            total_minutes=(row.total_seconds or 0) // 60,
            unique_users=row.unique_users or 0,
        ))

    return history


@router.post("/seed", response_model=SeedResponse)
async def trigger_seed(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SeedResponse:
    """Seed demo call data with revenue.

    Creates 50 users across pricing tiers with realistic call records.
    Idempotent - won't create duplicates if already seeded.
    """
    require_admin(current_user)

    logger.info("seed_triggered", admin_id=current_user.id)

    result = await seed_calls(db)

    if not result.get("seeded"):
        return SeedResponse(message="Data already seeded - use /reseed to refresh")

    return SeedResponse(
        message=f"Seeded {result['users_created']} users with {result['calls_created']} calls",
        users_created=result.get("users_created"),
        calls_created=result.get("calls_created"),
        total_revenue=float(result.get("total_revenue", 0)),
    )


@router.post("/reseed", response_model=SeedResponse)
async def trigger_reseed(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SeedResponse:
    """Clear and reseed demo call data.

    WARNING: Deletes all seeded users and their calls, then creates fresh data.
    """
    require_admin(current_user)

    logger.info("reseed_triggered", admin_id=current_user.id)

    result = await reseed_calls(db)

    return SeedResponse(
        message=f"Reseeded {result['users_created']} users with {result['calls_created']} calls (~${float(result.get('total_revenue', 0)):,.0f} revenue)",
        users_created=result.get("users_created"),
        calls_created=result.get("calls_created"),
        total_revenue=float(result.get("total_revenue", 0)),
    )
