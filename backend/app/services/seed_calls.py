"""Service for seeding realistic call data with revenue calculations.

Note: Uses standard random for demo data generation (not cryptographic).
"""
# ruff: noqa: S311

import random
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_password_hash
from app.models.call_record import CallDirection, CallRecord, CallStatus
from app.models.pricing_config import PricingConfig
from app.models.user import User

logger = structlog.get_logger()

# Pricing tier distribution for seeded users
TIER_DISTRIBUTION = [
    ("premium", 10),       # 10 premium users
    ("premium-mini", 15),  # 15 premium-mini users
    ("balanced", 15),      # 15 balanced users
    ("budget", 10),        # 10 budget users
]

# Call parameters for each tier (calls_per_user, avg_duration_min, demo_price_per_min)
# Demo prices set to generate ~$400K total across 6 months
TIER_CALL_PARAMS = {
    "premium": (200, 8, Decimal("3.00")),      # Enterprise: high volume, longer calls
    "premium-mini": (150, 6, Decimal("2.00")), # Business: medium-high volume
    "balanced": (120, 5, Decimal("1.50")),     # Standard: medium volume
    "budget": (80, 4, Decimal("1.00")),        # Starter: lower volume
}

# Phone number prefixes for realistic data
AREA_CODES = ["212", "310", "415", "305", "312", "702", "602", "206", "617", "404"]


def generate_phone() -> str:
    """Generate a realistic phone number."""
    area = random.choice(AREA_CODES)
    return f"+1{area}{random.randint(1000000, 9999999)}"


def generate_call_duration(avg_minutes: int) -> int:
    """Generate realistic call duration with variance."""
    # Use triangular distribution weighted toward average
    min_dur = 30  # 30 seconds minimum
    max_dur = avg_minutes * 60 * 2.5  # Max ~2.5x average
    mode = avg_minutes * 60  # Peak at average
    return max(int(random.triangular(min_dur, max_dur, mode)), 30)


async def ensure_pricing_tiers(db: AsyncSession) -> dict[str, PricingConfig]:
    """Ensure pricing tiers exist, create if missing."""
    result = await db.execute(select(PricingConfig))
    existing = {p.tier_id: p for p in result.scalars().all()}

    # Default tier configurations if not present
    default_tiers = {
        "premium": {
            "tier_name": "Premium",
            "base_llm": Decimal("0.024"),
            "base_stt": Decimal("0.003"),
            "base_tts": Decimal("0.003"),
            "base_tel": Decimal("0.008"),
            "ai_markup": Decimal("200"),
            "tel_markup": Decimal("25"),
        },
        "premium-mini": {
            "tier_name": "Premium Mini",
            "base_llm": Decimal("0.011"),
            "base_stt": Decimal("0.002"),
            "base_tts": Decimal("0.002"),
            "base_tel": Decimal("0.008"),
            "ai_markup": Decimal("300"),
            "tel_markup": Decimal("25"),
        },
        "balanced": {
            "tier_name": "Balanced",
            "base_llm": Decimal("0.014"),
            "base_stt": Decimal("0.003"),
            "base_tts": Decimal("0.003"),
            "base_tel": Decimal("0.008"),
            "ai_markup": Decimal("200"),
            "tel_markup": Decimal("25"),
        },
        "budget": {
            "tier_name": "Budget",
            "base_llm": Decimal("0.007"),
            "base_stt": Decimal("0.003"),
            "base_tts": Decimal("0.003"),
            "base_tel": Decimal("0.008"),
            "ai_markup": Decimal("200"),
            "tel_markup": Decimal("25"),
        },
    }

    for tier_id, config in default_tiers.items():
        if tier_id not in existing:
            pricing = PricingConfig(
                tier_id=tier_id,
                tier_name=config["tier_name"],
                base_llm_cost_per_minute=config["base_llm"],
                base_stt_cost_per_minute=config["base_stt"],
                base_tts_cost_per_minute=config["base_tts"],
                base_telephony_cost_per_minute=config["base_tel"],
                ai_markup_percentage=config["ai_markup"],
                telephony_markup_percentage=config["tel_markup"],
                final_ai_price_per_minute=Decimal("0"),
                final_telephony_price_per_minute=Decimal("0"),
                final_total_price_per_minute=Decimal("0"),
            )
            pricing.recalculate_prices()
            db.add(pricing)
            existing[tier_id] = pricing

    await db.flush()
    return existing


async def seed_calls(db: AsyncSession) -> dict[str, int | Decimal]:
    """Seed realistic call data with revenue across 6 months.

    Creates 50 users across pricing tiers with calls from Aug 2025 - Jan 2026.
    Revenue grows month-over-month: ~$15K (Aug) → ~$40K (Jan)
    """
    # Check if already seeded (look for seeded users)
    result = await db.execute(
        select(func.count(User.id)).where(User.email.like("%@seeded.spacevoice.ai"))
    )
    existing_seeded = result.scalar() or 0

    if existing_seeded > 0:
        logger.info("Call data already seeded", existing_users=existing_seeded)
        return {"seeded": False, "message": "Data already exists"}

    # Ensure pricing tiers exist
    pricing_tiers = await ensure_pricing_tiers(db)

    # Generate 6 months of dates (Aug 2025 - Jan 2026)
    now = datetime.now(UTC)
    current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Create list of 6 months going back from current
    from dateutil.relativedelta import relativedelta
    months = []
    for i in range(6):
        month_date = current_month - relativedelta(months=(5 - i))
        # Growth multiplier: 0.4 (oldest) → 1.0 (newest)
        growth_multiplier = 0.4 + (i * 0.12)  # 0.4, 0.52, 0.64, 0.76, 0.88, 1.0
        months.append((month_date, growth_multiplier))

    users_created = 0
    calls_created = 0
    total_revenue = Decimal("0")
    total_cost = Decimal("0")
    total_minutes = 0

    user_index = 0

    for tier_id, user_count in TIER_DISTRIBUTION:
        pricing = pricing_tiers.get(tier_id)
        if not pricing:
            logger.warning("Pricing tier %s not found, skipping", tier_id)
            continue

        calls_per_user, avg_duration, demo_price = TIER_CALL_PARAMS.get(tier_id, (80, 4, Decimal("0.50")))

        for _ in range(user_count):
            user_index += 1

            # Create seeded user with creation date spread across the 6 months
            # Users are created in different months for realistic timeline
            user_month_idx = user_index % 6  # Spread users across 6 months
            user_created_date = months[user_month_idx][0].replace(
                day=random.randint(1, 28),
                hour=random.randint(9, 17),
                minute=random.randint(0, 59),
            )

            user = User(
                email=f"user{user_index:03d}@seeded.spacevoice.ai",
                hashed_password=get_password_hash(secrets.token_urlsafe(16)),
                full_name=f"Seeded User {user_index}",
                company_name=f"Company {user_index}",
                is_active=True,
                is_superuser=False,
                onboarding_completed=True,
                created_at=user_created_date,
            )
            db.add(user)
            await db.flush()
            users_created += 1

            # Generate calls for this user across all 6 months
            for month_start, growth_mult in months:
                # Scale calls by growth multiplier (fewer calls in older months)
                month_calls = int((calls_per_user + random.randint(-20, 20)) * growth_mult)

                # Determine max day for this month (28 for safety, or current day if current month)
                is_current_month = month_start.month == now.month and month_start.year == now.year
                max_day = min(28, now.day) if is_current_month else 28

                for _ in range(month_calls):
                    # Random timestamp within the month
                    random_day = random.randint(1, max_day)
                    random_hour = random.randint(8, 20)  # Business hours-ish
                    random_minute = random.randint(0, 59)

                    call_time = month_start.replace(
                        day=random_day,
                        hour=random_hour,
                        minute=random_minute,
                    )

                    # Generate call details
                    duration_secs = generate_call_duration(avg_duration)
                    duration_mins = Decimal(str(duration_secs)) / 60

                    # Calculate revenue using demo pricing
                    revenue = (duration_mins * demo_price).quantize(Decimal("0.0001"))
                    # Cost is ~40% of revenue for realistic profit margins
                    cost = (revenue * Decimal("0.40")).quantize(Decimal("0.0001"))

                    # Determine call status (85% completed)
                    status_roll = random.random()
                    if status_roll < 0.85:
                        status = CallStatus.COMPLETED.value
                    elif status_roll < 0.92:
                        status = CallStatus.NO_ANSWER.value
                        duration_secs = 0
                        revenue = Decimal("0")
                        cost = Decimal("0")
                    elif status_roll < 0.97:
                        status = CallStatus.BUSY.value
                        duration_secs = 0
                        revenue = Decimal("0")
                        cost = Decimal("0")
                    else:
                        status = CallStatus.FAILED.value
                        duration_secs = 0
                        revenue = Decimal("0")
                        cost = Decimal("0")

                    # Direction (70% inbound, 30% outbound)
                    direction = (
                        CallDirection.INBOUND.value
                        if random.random() < 0.7
                        else CallDirection.OUTBOUND.value
                    )

                    call = CallRecord(
                        id=uuid.uuid4(),
                        user_id=user.id,
                        provider=random.choice(["telnyx", "twilio"]),
                        provider_call_id=f"call_{secrets.token_hex(16)}",
                        direction=direction,
                        status=status,
                        from_number=generate_phone(),
                        to_number=generate_phone(),
                        duration_seconds=duration_secs,
                        pricing_tier_id=tier_id,
                        price_per_minute=demo_price,
                        revenue_usd=revenue,
                        cost_usd=cost,
                        started_at=call_time,
                        answered_at=call_time if status == CallStatus.COMPLETED.value else None,
                        ended_at=(call_time + timedelta(seconds=duration_secs)) if status == CallStatus.COMPLETED.value else call_time,
                    )
                    db.add(call)

                    calls_created += 1
                total_revenue += revenue
                total_cost += cost
                if duration_secs > 0:
                    total_minutes += duration_secs // 60

    await db.commit()

    logger.info(
        "seed_calls_completed",
        users_created=users_created,
        calls_created=calls_created,
        total_revenue=float(total_revenue),
        total_cost=float(total_cost),
        total_minutes=total_minutes,
    )

    return {
        "seeded": True,
        "users_created": users_created,
        "calls_created": calls_created,
        "total_revenue": total_revenue,
        "total_cost": total_cost,
        "total_minutes": total_minutes,
        "profit": total_revenue - total_cost,
    }


async def reseed_calls(db: AsyncSession) -> dict[str, int | Decimal]:
    """Clear seeded data and reseed fresh."""
    logger.info("Clearing existing seeded data...")

    # Delete seeded users' calls first
    seeded_user_ids = await db.execute(
        select(User.id).where(User.email.like("%@seeded.spacevoice.ai"))
    )
    user_ids = [row[0] for row in seeded_user_ids.fetchall()]

    if user_ids:
        await db.execute(
            delete(CallRecord).where(CallRecord.user_id.in_(user_ids))
        )
        await db.execute(
            delete(User).where(User.id.in_(user_ids))
        )
        await db.commit()

    logger.info("Cleared seeded data", users_deleted=len(user_ids))

    # Now seed fresh data
    return await seed_calls(db)
