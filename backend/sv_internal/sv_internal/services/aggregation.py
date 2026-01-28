"""Aggregation service for computing income snapshots."""

from datetime import date
from decimal import Decimal

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sv_internal.models import SimClient, SimClientHistory, SimIncomeSnapshot

logger = structlog.get_logger()


async def compute_income_snapshots(db: AsyncSession) -> dict[str, int]:
    """Recompute income snapshots from client history data.

    This can be called to refresh the pre-computed aggregates if
    client data has been modified.
    """
    # Get all unique months from history
    result = await db.execute(
        select(SimClientHistory.month).distinct().order_by(SimClientHistory.month)
    )
    months = [row[0] for row in result.all()]

    if not months:
        logger.info("No history data to aggregate")
        return {"snapshots_created": 0}

    snapshots_created = 0

    for month in months:
        # Delete existing snapshot for this month
        existing = await db.execute(
            select(SimIncomeSnapshot).where(SimIncomeSnapshot.month == month)
        )
        existing_snapshot = existing.scalar_one_or_none()
        if existing_snapshot:
            await db.delete(existing_snapshot)

        # Aggregate history data for this month
        history_result = await db.execute(
            select(
                func.sum(SimClientHistory.mrr).label("total_mrr"),
                func.sum(SimClientHistory.paid_amount).label("total_revenue"),
                func.sum(SimClientHistory.refunds).label("total_refunds"),
                func.sum(SimClientHistory.chargebacks).label("total_chargebacks"),
                func.sum(SimClientHistory.net_revenue).label("total_net_revenue"),
                func.count(SimClientHistory.id).label("client_count"),
            ).where(SimClientHistory.month == month)
        )
        agg = history_result.one()

        total_mrr = Decimal(str(agg.total_mrr or 0))
        total_revenue = Decimal(str(agg.total_revenue or 0))
        total_refunds = Decimal(str(agg.total_refunds or 0))
        total_chargebacks = Decimal(str(agg.total_chargebacks or 0))
        total_net_revenue = Decimal(str(agg.total_net_revenue or 0))
        client_count = agg.client_count or 0

        # Count active clients (those with MRR > 0 this month)
        active_result = await db.execute(
            select(func.count(SimClientHistory.id)).where(
                SimClientHistory.month == month, SimClientHistory.mrr > 0
            )
        )
        active_clients = active_result.scalar() or 0

        # Get setup fees from clients who started this month
        setup_fees_result = await db.execute(
            select(func.sum(SimClient.setup_fee)).where(
                func.date_trunc("month", SimClient.onboarded_at) == month
            )
        )
        total_setup_fees = Decimal(str(setup_fees_result.scalar() or 0))

        # Count new clients this month
        new_result = await db.execute(
            select(func.count(SimClient.id)).where(
                func.date_trunc("month", SimClient.onboarded_at) == month
            )
        )
        new_clients = new_result.scalar() or 0

        # Count churned clients this month (had MRR last month, no MRR this month)
        # This is a simplified calculation
        churned_result = await db.execute(
            select(func.count(SimClient.id)).where(SimClient.status == "churned")
        )
        churned_clients = churned_result.scalar() or 0 if month == months[-1] else 0

        avg_revenue_per_client = (
            (total_net_revenue / active_clients).quantize(Decimal("0.01"))
            if active_clients > 0
            else Decimal("0")
        )

        snapshot = SimIncomeSnapshot(
            month=month,
            total_mrr=total_mrr,
            total_arr=total_mrr * 12,
            total_revenue=total_revenue,
            total_setup_fees=total_setup_fees,
            total_refunds=total_refunds,
            total_chargebacks=total_chargebacks,
            total_net_revenue=total_net_revenue,
            active_clients=active_clients,
            new_clients=new_clients,
            churned_clients=churned_clients,
            avg_revenue_per_client=avg_revenue_per_client,
        )
        db.add(snapshot)
        snapshots_created += 1

    await db.commit()

    logger.info("aggregation_completed", snapshots_created=snapshots_created)
    return {"snapshots_created": snapshots_created}
