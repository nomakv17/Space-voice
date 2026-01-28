"""Income summary and platform-wide statistics."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from sv_internal.models import SimClient, SimIncomeSnapshot
from sv_internal.services.seed import seed_clients

router = APIRouter(prefix="/api/v1/internal", tags=["internal"])
logger = structlog.get_logger()

# Type alias for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: User) -> None:
    """Require superuser access."""
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )


class IncomeSummaryResponse(BaseModel):
    """Platform-wide income summary."""

    total_mrr: float
    total_arr: float
    total_net_revenue: float
    total_setup_fees: float
    active_clients: int
    mrr_growth_pct: float
    avg_revenue_per_client: float


class IncomeHistoryResponse(BaseModel):
    """Monthly income history item."""

    month: str
    total_mrr: float
    total_arr: float
    total_revenue: float
    total_setup_fees: float
    total_refunds: float
    total_chargebacks: float
    total_net_revenue: float
    active_clients: int
    new_clients: int
    churned_clients: int


@router.get("/income/summary", response_model=IncomeSummaryResponse)
async def get_income_summary(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> IncomeSummaryResponse:
    """Get platform-wide income summary from current client data."""
    require_admin(current_user)

    # Aggregate from active clients
    result = await db.execute(
        select(
            func.sum(SimClient.mrr).label("total_mrr"),
            func.sum(SimClient.setup_fee).label("total_setup_fees"),
            func.sum(SimClient.net_revenue).label("total_net_revenue"),
            func.count(SimClient.id).label("active_clients"),
        ).where(SimClient.status == "active")
    )
    row = result.one()

    total_mrr = float(row.total_mrr or 0)
    total_setup_fees = float(row.total_setup_fees or 0)
    total_net_revenue = float(row.total_net_revenue or 0)
    active_clients = row.active_clients or 0

    # Get MRR growth from snapshots
    snapshots = await db.execute(
        select(SimIncomeSnapshot).order_by(SimIncomeSnapshot.month.desc()).limit(2)
    )
    snapshot_list = snapshots.scalars().all()

    mrr_growth_pct = 0.0
    if len(snapshot_list) >= 2:
        current_mrr = float(snapshot_list[0].total_mrr)
        prev_mrr = float(snapshot_list[1].total_mrr)
        if prev_mrr > 0:
            mrr_growth_pct = ((current_mrr - prev_mrr) / prev_mrr) * 100

    avg_revenue = total_net_revenue / active_clients if active_clients > 0 else 0.0

    return IncomeSummaryResponse(
        total_mrr=total_mrr,
        total_arr=total_mrr * 12,
        total_net_revenue=total_net_revenue,
        total_setup_fees=total_setup_fees,
        active_clients=active_clients,
        mrr_growth_pct=round(mrr_growth_pct, 2),
        avg_revenue_per_client=round(avg_revenue, 2),
    )


@router.get("/income/history", response_model=list[IncomeHistoryResponse])
async def get_income_history(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[IncomeHistoryResponse]:
    """Get 6-month platform-wide income history."""
    require_admin(current_user)

    result = await db.execute(
        select(SimIncomeSnapshot).order_by(SimIncomeSnapshot.month.desc()).limit(6)
    )
    snapshots = result.scalars().all()

    return [
        IncomeHistoryResponse(
            month=s.month.isoformat(),
            total_mrr=float(s.total_mrr),
            total_arr=float(s.total_arr),
            total_revenue=float(s.total_revenue),
            total_setup_fees=float(s.total_setup_fees),
            total_refunds=float(s.total_refunds),
            total_chargebacks=float(s.total_chargebacks),
            total_net_revenue=float(s.total_net_revenue),
            active_clients=s.active_clients,
            new_clients=s.new_clients,
            churned_clients=s.churned_clients,
        )
        for s in snapshots
    ]


@router.post("/seed")
async def trigger_seed(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Seed simulated client data (idempotent)."""
    require_admin(current_user)

    log = logger.bind(admin_id=current_user.id)
    log.info("seed_triggered")

    result = await seed_clients(db)

    log.info("seed_completed", **result)
    return {
        "message": f"Seeded {result['clients_created']} clients with {result['history_records']} history records"
    }
