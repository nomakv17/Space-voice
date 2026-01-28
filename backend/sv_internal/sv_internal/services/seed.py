"""Seed service for generating simulated client data."""

import random
import secrets
import string
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import structlog
from dateutil.relativedelta import relativedelta
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_password_hash
from app.models.user import User
from sv_internal.models import SimClient, SimClientHistory, SimIncomeSnapshot

logger = structlog.get_logger()

# Industries for descriptors
INDUSTRIES = [
    "HVAC",
    "Plumbing",
    "Electrical",
    "Roofing",
    "Landscaping",
    "General Contracting",
    "Pool Service",
    "Pest Control",
    "Cleaning",
    "Security",
]

# Pricing tiers
PRICING_TIERS = ["budget", "balanced", "premium-mini", "premium"]


def generate_client_id() -> str:
    """Generate a unique client ID in format SV-XXXXXX."""
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=6))
    return f"SV-{suffix}"


def generate_stripe_id(prefix: str, length: int = 24) -> str:
    """Generate a Stripe-like ID."""
    return f"{prefix}_{secrets.token_hex(length // 2)}"


async def seed_clients(db: AsyncSession) -> dict[str, int]:
    """Seed simulated client data.

    Creates 50 clients:
    - 35 enterprise (MRR $300-$2,000)
    - 15 medium (MRR $49-$299)
    - 2-3 churned, 1 paused, rest active

    Each client gets 6 months of history data.
    """
    # Check if already seeded
    result = await db.execute(select(func.count(SimClient.id)))
    existing_count = result.scalar() or 0

    if existing_count > 0:
        logger.info("Data already seeded", existing_clients=existing_count)
        return {"clients_created": 0, "history_records": 0, "skipped": True}

    clients_created = 0
    history_records = 0

    # Generate 6 months of history ending in current month (e.g., Aug 2025 - Jan 2026)
    today = date.today()
    current_month_start = today.replace(day=1)
    months = []
    for i in range(6):
        # Go back (5-i) months from current month using proper month arithmetic
        month_date = current_month_start - relativedelta(months=(5 - i))
        months.append(month_date)

    # Create 50 clients - realistic mix
    enterprise_count = 35  # 70% enterprise
    medium_count = 15      # 30% medium
    churned_count = 3      # 3 churned (6%)
    paused_count = 2       # 2 paused

    all_clients: list[SimClient] = []
    # Store histories separately to avoid async relationship loading issues
    client_histories: dict[int, list[SimClientHistory]] = {}

    for i in range(50):
        is_enterprise = i < enterprise_count
        client_size = "enterprise" if is_enterprise else "medium"
        industry = random.choice(INDUSTRIES)
        descriptor = f"{client_size.title()} {industry}"

        # Determine status
        if i < churned_count:
            status = "churned"
        elif i < churned_count + paused_count:
            status = "paused"
        else:
            status = "active"

        # Generate MRR based on size - realistic SaaS pricing
        if is_enterprise:
            # Enterprise: $300-$2,000/month, weighted toward $800
            mrr = Decimal(str(random.triangular(300, 2000, 800)))
            setup_fee = Decimal(str(random.randint(99, 499)))
        else:
            # Medium: $49-$299/month, weighted toward $149
            mrr = Decimal(str(random.triangular(49, 299, 149)))
            setup_fee = Decimal(str(random.randint(0, 99)))

        mrr = mrr.quantize(Decimal("0.01"))
        setup_fee = setup_fee.quantize(Decimal("0.01"))
        arr = mrr * 12
        total_first_month = mrr + setup_fee

        # Onboarded 6-7 months ago
        onboarded_at = datetime.now(UTC) - timedelta(
            days=random.randint(180, 210)
        )

        # Payment processor fields
        billing_cycle = random.choices(["monthly", "annual"], weights=[80, 20])[0]
        payment_method = random.choices(["card", "ach", "wire"], weights=[70, 20, 10])[
            0
        ]
        last_charge_status = "succeeded" if status == "active" else "failed"

        # Create client
        client = SimClient(
            client_id=generate_client_id(),
            client_size=client_size,
            industry=industry,
            descriptor=descriptor,
            status=status,
            onboarded_at=onboarded_at,
            processor="stripe",
            customer_id=generate_stripe_id("cus"),
            subscription_id=generate_stripe_id("sub"),
            plan_id=generate_stripe_id("price", 16),
            billing_cycle=billing_cycle,
            next_charge_date=today + timedelta(days=random.randint(1, 30)),
            last_charge_date=today - timedelta(days=random.randint(1, 30)),
            last_charge_status=last_charge_status,
            payment_method_type=payment_method,
            billing_currency="usd",
            mrr=mrr if status != "churned" else Decimal("0"),
            arr=arr if status != "churned" else Decimal("0"),
            setup_fee=setup_fee,
            total_first_month=total_first_month,
            pricing_tier=random.choice(PRICING_TIERS),
        )

        # Generate 6 months of history
        total_paid = Decimal("0")
        total_refunded = Decimal("0")
        total_chargebacks = Decimal("0")
        monthly_histories = []

        for month_idx, month in enumerate(months):
            # Base MRR with visible growth (5-12% monthly for demo purposes)
            # This makes month-over-month changes noticeable in the UI
            growth_factor = Decimal(str(1 + random.uniform(0.05, 0.12) * month_idx))
            month_mrr = (mrr * growth_factor).quantize(Decimal("0.01"))

            # For churned clients, MRR drops to 0 in month 5 or 6
            if status == "churned" and month_idx >= 4:
                month_mrr = Decimal("0")

            # Invoiced amount (first month includes setup fee)
            invoiced = month_mrr
            if month_idx == 0:
                invoiced = invoiced + setup_fee

            # Paid amount (occasional failures)
            paid = invoiced
            if random.random() < 0.05:  # 5% chance of partial payment
                paid = (invoiced * Decimal("0.9")).quantize(Decimal("0.01"))

            # Refunds (~5% of months)
            refunds = Decimal("0")
            if random.random() < 0.05:
                refunds = Decimal(str(random.randint(50, 500)))

            # Chargebacks (~2% of months)
            chargebacks = Decimal("0")
            if random.random() < 0.02:
                chargebacks = Decimal(str(random.randint(100, 300)))

            net_revenue = paid - refunds - chargebacks

            # Usage data - realistic call volumes
            if is_enterprise:
                calls_handled = random.randint(100, 800)  # Enterprise: 100-800 calls/month
            else:
                calls_handled = random.randint(20, 200)   # Medium: 20-200 calls/month

            avg_duration = random.uniform(90, 360)  # 1.5-6 minutes average
            total_minutes = calls_handled * avg_duration / 60

            history = SimClientHistory(
                client_id=client.id,  # Will be set after client is added
                month=month,
                invoiced_amount=invoiced,
                paid_amount=paid,
                mrr=month_mrr,
                refunds=refunds,
                chargebacks=chargebacks,
                net_revenue=net_revenue,
                calls_handled=calls_handled,
                total_minutes=Decimal(str(total_minutes)).quantize(Decimal("0.01")),
                avg_call_duration=Decimal(str(avg_duration)).quantize(Decimal("0.01")),
            )
            monthly_histories.append(history)

            total_paid += paid
            total_refunded += refunds
            total_chargebacks += chargebacks

        # Update client with lifetime totals
        client.paid_amount = total_paid
        client.refunded_amount = total_refunded
        client.chargebacks_amount = total_chargebacks
        client.net_revenue = total_paid - total_refunded - total_chargebacks
        client.invoice_count = 6
        client.payment_count = 6
        client.successful_payments = 5 if status == "active" else 4
        client.failed_payments = 1 if status != "active" else 0

        # 30-day stats from most recent month
        if monthly_histories:
            last_month = monthly_histories[-1]
            client.calls_received_30d = int(last_month.calls_handled * 1.1)
            client.calls_handled_30d = last_month.calls_handled
            client.avg_call_duration = float(last_month.avg_call_duration)
            client.total_minutes_30d = float(last_month.total_minutes)

        # Add client to session
        db.add(client)
        await db.flush()  # Get the client ID

        # Now set the client_id on histories and add them
        for history in monthly_histories:
            history.client_id = client.id
            db.add(history)
            history_records += 1

        # Store histories for snapshot computation (avoids async relationship issues)
        client_histories[client.id] = monthly_histories

        all_clients.append(client)
        clients_created += 1

        # Create matching User for the client
        user = User(
            email=f"{client.client_id.lower()}@client.spacevoice.ai",
            hashed_password=get_password_hash("clientpassword123"),
            full_name=descriptor,
            is_active=status == "active",
            is_superuser=False,
            onboarding_completed=True,
            onboarding_step=5,
        )
        db.add(user)
        await db.flush()

        # Link user to client
        client.user_id = user.id

    # Compute and save income snapshots
    for month in months:
        # Aggregate data for this month
        active_mrr = Decimal("0")
        total_revenue = Decimal("0")
        setup_fees = Decimal("0")
        refunds = Decimal("0")
        chargebacks = Decimal("0")
        active_count = 0
        new_count = 0
        churned_count_month = 0

        for client in all_clients:
            for history in client_histories.get(client.id, []):
                if history.month == month:
                    if client.status == "active" or (
                        client.status == "churned" and history.mrr > 0
                    ):
                        active_mrr += history.mrr
                        active_count += 1
                    total_revenue += history.paid_amount
                    refunds += history.refunds
                    chargebacks += history.chargebacks

                    # First month has setup fees
                    if month == months[0]:
                        setup_fees += client.setup_fee

        net_revenue = total_revenue - refunds - chargebacks
        avg_per_client = (
            net_revenue / active_count if active_count > 0 else Decimal("0")
        )

        # New clients (appeared this month)
        if month == months[0]:
            new_count = len(all_clients)

        # Churned this month
        if month == months[-1]:
            churned_count_month = churned_count

        snapshot = SimIncomeSnapshot(
            month=month,
            total_mrr=active_mrr,
            total_arr=active_mrr * 12,
            total_revenue=total_revenue,
            total_setup_fees=setup_fees,
            total_refunds=refunds,
            total_chargebacks=chargebacks,
            total_net_revenue=net_revenue,
            active_clients=active_count,
            new_clients=new_count,
            churned_clients=churned_count_month,
            avg_revenue_per_client=avg_per_client.quantize(Decimal("0.01")),
        )
        db.add(snapshot)

    await db.commit()

    logger.info(
        "seed_completed",
        clients_created=clients_created,
        history_records=history_records,
    )

    return {
        "clients_created": clients_created,
        "history_records": history_records,
        "skipped": False,
    }
